from __future__ import annotations

import mimetypes
from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiohttp
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.brand import STORE_DESCRIPTION, STORE_NAME
from app.config import Settings, load_settings
from app.database.models import ProductCategory
from app.database.repositories.orders import OrderRepository
from app.database.repositories.products import ProductRepository
from app.database.repositories.users import UserRepository
from app.database.session import create_engine
from app.services.order_service import OrderDraftItem, OrderService, OrderValidationError, TelegramCustomer
from app.utils.logging import configure_logging
from app.web.auth import WebAppAuthError, validate_init_data
from app.web.schemas import (
    CategoryResponse,
    OrderCreateRequest,
    OrderCreateResponse,
    ProductResponse,
    StoreMetaResponse,
    WebAppUserResponse,
    WebAppValidateRequest,
    WebAppValidateResponse,
)
from app.web.serializers import category_response, product_response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = load_settings()
    configure_logging(settings.log_level)
    engine = create_engine(settings)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    yield
    await engine.dispose()


app = FastAPI(
    title="Telegram Store Manager Mini App API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.session_factory


async def get_session(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@app.get("/api/health")
async def healthcheck() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/meta", response_model=StoreMetaResponse)
async def get_meta(settings: Settings = Depends(get_settings)) -> StoreMetaResponse:
    return StoreMetaResponse(
        shop_name=STORE_NAME,
        shop_description=STORE_DESCRIPTION,
        support_url=settings.support_url,
        reviews_url=settings.reviews_url,
        tiktok_url=settings.tiktok_url,
        mini_app_url=settings.mini_app_url,
    )


@app.get("/api/categories", response_model=list[CategoryResponse])
async def list_categories() -> list[CategoryResponse]:
    return [category_response(category) for category in ProductCategory]


@app.get("/api/products", response_model=list[ProductResponse])
async def list_products(session: AsyncSession = Depends(get_session)) -> list[ProductResponse]:
    products = await ProductRepository(session).list_public_products()
    return [product_response(product) for product in products]


@app.get("/api/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, session: AsyncSession = Depends(get_session)) -> ProductResponse:
    product = await ProductRepository(session).get_public_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Товар не найден.")
    return product_response(product)


@app.post("/api/webapp/validate", response_model=WebAppValidateResponse)
async def validate_webapp(
    payload: WebAppValidateRequest,
    settings: Settings = Depends(get_settings),
) -> WebAppValidateResponse:
    try:
        auth = validate_init_data(payload.init_data, bot_token=settings.bot_token)
    except WebAppAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return WebAppValidateResponse(
        ok=True,
        user=WebAppUserResponse(
            id=auth.user.id,
            first_name=auth.user.first_name,
            username=auth.user.username,
            last_name=auth.user.last_name,
        ),
    )


@app.post("/api/orders", response_model=OrderCreateResponse)
async def create_order(
    payload: OrderCreateRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> OrderCreateResponse:
    auth = None
    if payload.init_data:
        try:
            auth = validate_init_data(payload.init_data, bot_token=settings.bot_token)
        except WebAppAuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    service = OrderService(
        session=session,
        settings=settings,
        products=ProductRepository(session),
        users=UserRepository(session),
        orders=OrderRepository(session),
    )
    try:
        order = await service.create_order(
            customer=TelegramCustomer(
                telegram_id=auth.user.id if auth else 0,
                username=auth.user.username if auth else None,
                first_name=auth.user.first_name if auth else None,
            ),
            name=payload.name,
            username=payload.username,
            phone=payload.phone,
            comment=payload.comment,
            contact_method=payload.contact_method,
            items=[OrderDraftItem(product_id=item.product_id, quantity=item.quantity) for item in payload.items],
        )
    except OrderValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return OrderCreateResponse(
        ok=True,
        order_id=order.id,
        total_amount=order.total_amount,
        message="Заказ создан.",
    )


@app.get("/api/media/{photo_id}")
async def get_media(
    photo_id: int,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    photo = await ProductRepository(session).get_photo_by_id(photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Фото не найдено.")

    api_url = f"https://api.telegram.org/bot{settings.bot_token}/getFile"
    async with aiohttp.ClientSession() as client:
        async with client.get(api_url, params={"file_id": photo.file_id}) as response:
            if response.status != 200:
                raise HTTPException(status_code=502, detail="Не удалось получить файл из Telegram.")
            payload = await response.json()
            result = payload.get("result") or {}
            file_path = result.get("file_path")
            if not file_path:
                raise HTTPException(status_code=404, detail="Telegram не вернул путь к файлу.")

        file_url = f"https://api.telegram.org/file/bot{settings.bot_token}/{file_path}"
        async with client.get(file_url) as file_response:
            if file_response.status != 200:
                raise HTTPException(status_code=502, detail="Не удалось скачать файл из Telegram.")
            media_type = file_response.headers.get("Content-Type") or mimetypes.guess_type(file_path)[0] or "image/jpeg"
            content = await file_response.read()
            return Response(content=content, media_type=media_type)
