from __future__ import annotations

import asyncio
import hashlib
import io
import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import aiohttp
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import Settings
from app.utils.logging import get_logger


class MediaVariant(StrEnum):
    CARD = "card"
    DETAIL = "detail"
    THUMB = "thumb"


@dataclass(frozen=True, slots=True)
class MediaAsset:
    content: bytes
    media_type: str
    etag: str


class MediaUnavailableError(RuntimeError):
    pass


class MediaOptimizer:
    ALGORITHM_VERSION = "webp-v1"
    MAX_SOURCE_BYTES = 20 * 1024 * 1024
    MAX_PIXELS = 40_000_000
    PROFILES = {
        MediaVariant.CARD: (640, 85),
        MediaVariant.DETAIL: (1600, 88),
        MediaVariant.THUMB: (200, 81),
    }

    def __init__(self, *, settings: Settings, client: aiohttp.ClientSession) -> None:
        self.settings = settings
        self.client = client
        self.root = Path(settings.media_cache_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, asyncio.Lock] = {}
        self._source_locks: dict[str, asyncio.Lock] = {}
        self.logger = get_logger("app.media_optimizer")

    async def get_product(self, file_id: str, photo_id: int, variant: MediaVariant) -> MediaAsset:
        return await self._get(file_id=file_id, identity=f"photo-{photo_id}", variant=variant)

    async def get_store(self, file_id: str, kind: str, version: str) -> MediaAsset:
        variant = MediaVariant.DETAIL
        return await self._get(file_id=file_id, identity=f"store-{kind}-{version}", variant=variant, max_side=320 if kind == "avatar" else 1600)

    async def _get(self, *, file_id: str, identity: str, variant: MediaVariant, max_side: int | None = None) -> MediaAsset:
        key = hashlib.sha256(f"{self.ALGORITHM_VERSION}|{identity}|{variant}|{file_id}".encode()).hexdigest()
        cached = self._read_cache(key)
        if cached:
            return cached
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = self._read_cache(key)
            if cached:
                return cached
            source = await self._source(file_id)
            side, quality = self.PROFILES[variant]
            try:
                content = await asyncio.to_thread(self._to_webp, source, max_side or side, quality)
                media_type = "image/webp"
                suffix = "webp"
                if len(content) >= len(source):
                    content, media_type, suffix = source, "image/jpeg", "orig"
            except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
                self.logger.warning("media_optimization_failed", media_key=key[:12])
                content, media_type, suffix = source, "image/jpeg", "orig"
            self._write_cache(key, suffix, content)
            await asyncio.to_thread(self._trim_cache)
            return MediaAsset(content=content, media_type=media_type, etag=hashlib.sha256(content).hexdigest())

    async def _source(self, file_id: str) -> bytes:
        source_key = hashlib.sha256(file_id.encode()).hexdigest()
        source_path = self.root / "source" / f"{source_key}.bin"
        if source_path.exists():
            return await asyncio.to_thread(source_path.read_bytes)
        lock = self._source_locks.setdefault(source_key, asyncio.Lock())
        async with lock:
            if source_path.exists():
                return await asyncio.to_thread(source_path.read_bytes)
            return await self._download_source(file_id, source_path)

    async def _download_source(self, file_id: str, source_path: Path) -> bytes:
        source_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            async with self.client.get("https://api.telegram.org/bot{}/getFile".format(self.settings.bot_token), params={"file_id": file_id}) as response:
                payload = await response.json()
            file_path = (payload.get("result") or {}).get("file_path")
            if not file_path:
                raise MediaUnavailableError
            async with self.client.get("https://api.telegram.org/file/bot{}/{}".format(self.settings.bot_token, file_path)) as response:
                if response.status != 200:
                    raise MediaUnavailableError
                chunks: list[bytes] = []
                total = 0
                async for chunk in response.content.iter_chunked(64 * 1024):
                    total += len(chunk)
                    if total > self.MAX_SOURCE_BYTES:
                        raise MediaUnavailableError
                    chunks.append(chunk)
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise MediaUnavailableError from exc
        content = b"".join(chunks)
        await asyncio.to_thread(self._atomic_write, source_path, content)
        return content

    @classmethod
    def _to_webp(cls, source: bytes, max_side: int, quality: int) -> bytes:
        Image.MAX_IMAGE_PIXELS = cls.MAX_PIXELS
        with Image.open(io.BytesIO(source)) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            has_alpha = "A" in image.getbands()
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if has_alpha else "RGB")
            output = io.BytesIO()
            image.save(output, "WEBP", quality=quality, method=6, lossless=has_alpha and image.width * image.height < 400_000)
            return output.getvalue()

    def _read_cache(self, key: str) -> MediaAsset | None:
        for suffix, media_type in (("webp", "image/webp"), ("orig", "image/jpeg")):
            path = self.root / "variant" / f"{key}.{suffix}"
            if path.exists():
                content = path.read_bytes()
                os.utime(path, None)
                return MediaAsset(content=content, media_type=media_type, etag=hashlib.sha256(content).hexdigest())
        return None

    def _write_cache(self, key: str, suffix: str, content: bytes) -> None:
        self._atomic_write(self.root / "variant" / f"{key}.{suffix}", content)

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(content)
        temporary.replace(path)

    def _trim_cache(self) -> None:
        limit = self.settings.media_cache_max_mb * 1024 * 1024
        files = [path for path in self.root.rglob("*") if path.is_file() and not path.name.endswith(".tmp")]
        total = sum(path.stat().st_size for path in files)
        for path in sorted(files, key=lambda item: item.stat().st_atime):
            if total <= limit:
                break
            total -= path.stat().st_size
            path.unlink(missing_ok=True)
