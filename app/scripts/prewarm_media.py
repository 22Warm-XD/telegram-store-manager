from __future__ import annotations

import argparse
import asyncio

import aiohttp
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import load_settings
from app.database.repositories.products import ProductRepository
from app.database.session import create_engine
from app.services.media_optimizer import MediaOptimizer, MediaUnavailableError, MediaVariant


async def run(active_only: bool) -> tuple[int, int, int]:
    settings = load_settings()
    engine = create_engine(settings)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        products = await ProductRepository(session).list_public_products()
    photos = [photo for product in products for photo in product.photos]
    success = skipped = failed = 0
    timeout = aiohttp.ClientTimeout(total=20, connect=5, sock_read=15)
    async with aiohttp.ClientSession(timeout=timeout) as client:
        optimizer = MediaOptimizer(settings=settings, client=client)
        semaphore = asyncio.Semaphore(3)
        async def warm(photo, variant: MediaVariant) -> bool:
            async with semaphore:
                await optimizer.get_product(photo.file_id, photo.id, variant)
                return True
        tasks = [warm(product.photos[0], MediaVariant.CARD) for product in products if product.photos]
        tasks += [warm(photo, variant) for photo in photos for variant in (MediaVariant.THUMB, MediaVariant.DETAIL)]
        for result in await asyncio.gather(*tasks, return_exceptions=True):
            if result is True:
                success += 1
            elif isinstance(result, MediaUnavailableError):
                failed += 1
            else:
                failed += 1
    await engine.dispose()
    return success, skipped, failed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--active-only", action="store_true")
    args = parser.parse_args()
    success, skipped, failed = asyncio.run(run(args.active_only))
    print(f"success={success} skipped={skipped} failed={failed}")


if __name__ == "__main__":
    main()
