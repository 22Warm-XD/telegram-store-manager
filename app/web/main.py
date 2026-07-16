from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiohttp
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, load_settings
from app.database.models import CryptoNetwork, ProductCategory
from app.database.repositories.orders import OrderRepository
from app.database.repositories.products import ProductRepository
from app.database.repositories.users import UserRepository
from app.database.repositories.store_settings import StoreSettingsRepository
from app.database.session import create_engine
from app.services.order_service import OrderDraftItem, OrderService, OrderValidationError, TelegramCustomer
from app.services.media_optimizer import MediaOptimizer, MediaUnavailableError, MediaVariant
from app.utils.logging import configure_logging
from app.web.auth import WebAppAuthError, validate_init_data
from app.web.schemas import (
    CategoryResponse,
    OrderCreateRequest,
    OrderCreateResponse,
    PaymentOptionsResponse,
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
    client = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20, connect=5, sock_read=15))
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.media_optimizer = MediaOptimizer(settings=settings, client=client)
    yield
    await client.close()
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


def get_media_optimizer(request: Request) -> MediaOptimizer:
    return request.app.state.media_optimizer


async def get_session(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@app.get("/api/health")
async def healthcheck() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/meta", response_model=StoreMetaResponse)
async def get_meta(
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> StoreMetaResponse:
    store_settings = await StoreSettingsRepository(session).get()
    return StoreMetaResponse(
        shop_name="Kuznetsky Store",
        support_url=settings.support_url,
        reviews_url=settings.reviews_url,
        tiktok_url=settings.tiktok_url,
        mini_app_url=settings.mini_app_url,
        background_color=store_settings.background_color,
        avatar_url=f"/api/store-media/avatar?v={int(store_settings.updated_at.timestamp())}" if store_settings.avatar_file_id else "/kuznetsky-avatar.jpg",
        cover_url=f"/api/store-media/cover?v={int(store_settings.updated_at.timestamp())}" if store_settings.cover_file_id else None,
        payment_options=PaymentOptionsResponse(
            card_available=bool(settings.payment_card_number.strip()),
            card_number=settings.payment_card_number.strip() or None,
            card_holder=settings.payment_card_holder.strip() or None,
            phone_available=bool(settings.payment_phone_number.strip()),
            phone_number=settings.payment_phone_number.strip() or None,
            phone_holder=settings.payment_phone_holder.strip() or None,
            crypto_networks={
                network: wallet
                for network, wallet in {
                    CryptoNetwork.BEP20: settings.payment_crypto_bep20.strip(),
                    CryptoNetwork.TRC20: settings.payment_crypto_trc20.strip(),
                    CryptoNetwork.TON: settings.payment_crypto_ton.strip(),
                }.items()
                if wallet
            },
        ),
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
            delivery_provider=payload.delivery_provider,
            delivery_address=payload.delivery_address,
            payment_method=payload.payment_method,
            crypto_network=payload.crypto_network,
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
    variant: MediaVariant = MediaVariant.DETAIL,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
    optimizer: MediaOptimizer = Depends(get_media_optimizer),
) -> Response:
    photo = await ProductRepository(session).get_photo_by_id(photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Фото не найдено.")

    try:
        return await _media_response(await optimizer.get_product(photo.file_id, photo.id, variant), request)
    except MediaUnavailableError as exc:
        raise HTTPException(status_code=502, detail="Не удалось получить изображение.") from exc


@app.get("/api/store-media/{kind}")
async def get_store_media(
    kind: str,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
    optimizer: MediaOptimizer = Depends(get_media_optimizer),
) -> Response:
    store_settings = await StoreSettingsRepository(session).get()
    file_id = {
        "avatar": store_settings.avatar_file_id,
        "cover": store_settings.cover_file_id,
    }.get(kind)
    if not file_id:
        raise HTTPException(status_code=404, detail="Store media not found.")
    if kind not in {"avatar", "cover"}:
        raise HTTPException(status_code=404, detail="Store media not found.")
    try:
        return await _media_response(await optimizer.get_store(file_id, kind, str(int(store_settings.updated_at.timestamp()))), request)
    except MediaUnavailableError as exc:
        raise HTTPException(status_code=502, detail="Не удалось получить изображение.") from exc


async def _media_response(asset, request: Request | None = None) -> Response:
    if request is not None and request.headers.get("if-none-match") == f'"{asset.etag}"':
        return Response(status_code=304, headers={"ETag": f'"{asset.etag}"'})
    return Response(
        content=asset.content,
        media_type=asset.media_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable", "ETag": f'"{asset.etag}"', "Content-Length": str(len(asset.content))},
    )
