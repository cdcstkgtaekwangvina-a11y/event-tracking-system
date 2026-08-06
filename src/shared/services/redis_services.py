import os
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime
from typing import Annotated, Any, cast

import orjson
import redis.asyncio as redis
from dotenv import load_dotenv
from fastapi import Depends
from pydantic import BaseModel

from src.shared.base.base_logger import get_logger
from src.shared.constants.cache_tags import CacheTags
from src.shared.schemas.pagination_schemas import (
    CursorPaginationRequest,
    PaginationRequest,
)

load_dotenv()

logger = get_logger(__name__)


class RedisServices:
    url: str = os.environ["REDIS_URL"]

    def __init__(self):
        pool = redis.ConnectionPool.from_url(
            self.url, max_connections=30, decode_responses=True
        )
        self.client = redis.Redis.from_pool(connection_pool=pool)
        self.tag_version_prefix = "tag_version:"

    @staticmethod
    def _orjson_default(obj: Any) -> Any:
        if hasattr(obj, "_mapping"):
            return dict(obj._mapping)
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        if obj.__class__.__name__ == "UUID":
            return str(obj)
        raise TypeError(f"Type {obj.__class__.__name__} not serializable")

    # ──────────────────────────────────────────────
    # Tag Version helpers
    # ──────────────────────────────────────────────

    async def _get_tag_versions(self, tags: Sequence[str]) -> dict[str, int]:
        """Fetch current versions for a list of tags in one pipeline round-trip.

        Returns a dict mapping tag_name -> version (int).
        Tags that don't exist yet in Redis are treated as version 0.
        """
        if not tags:
            return {}

        async with self.client.pipeline(transaction=False) as pipe:
            for tag in tags:
                pipe.get(f"{self.tag_version_prefix}{tag}")
            results = await pipe.execute()

        return {
            str(tag): int(version) if version is not None else 0
            for tag, version in zip(tags, results)
        }

    async def _validate_tag_versions(self, saved_tags: dict[str, int]) -> bool:
        """Compare saved tag versions against live versions in Redis.

        Returns True if ALL versions match, False otherwise.
        Per the spec: if current version is null (key doesn't exist)
        OR differs from saved version -> data is stale.
        """
        if not saved_tags:
            return True

        if isinstance(saved_tags, list):
            return False

        tag_names = list(saved_tags.keys())

        async with self.client.pipeline(transaction=False) as pipe:
            for tag in tag_names:
                pipe.get(f"{self.tag_version_prefix}{tag}")
            results = await pipe.execute()

        for tag, current_raw in zip(tag_names, results):
            saved_version = saved_tags[tag]

            # null (key không tồn tại) -> dữ liệu lỗi thời
            if current_raw is None:
                return False

            current_version = int(current_raw)

            # Version khác -> dữ liệu lỗi thời
            if current_version != saved_version:
                return False

        return True

    # ──────────────────────────────────────────────
    # SET: Lưu envelope kèm tag versions snapshot
    # ──────────────────────────────────────────────

    async def _set_envelope(
        self,
        key: str,
        value: Any,
        logical_expires_at: float | None,
        tags: Sequence[str] | None = None,
        **kwargs,
    ):
        tag_versions = await self._get_tag_versions(tags) if tags else {}

        if tags:
            async with self.client.pipeline(transaction=False) as pipe:
                for tag in tags:
                    tag_key = f"{self.tag_version_prefix}{tag}"
                    pipe.setnx(tag_key, 0)
                    pipe.expire(tag_key, 86400)
                await pipe.execute()

            tag_versions = await self._get_tag_versions(tags)

        envelope = {
            "value": value,
            "logical_expires_at": logical_expires_at,
            "tags": tag_versions,  # dict {tag_name: version} thay vì list
        }
        serialized_data = orjson.dumps(envelope, default=self._orjson_default)

        # Calculate physical TTL for Redis key auto-expiration
        if logical_expires_at is not None:
            now = datetime.now().timestamp()
            # Add 300s buffer so stale-while-revalidate can still use expired data
            physical_ttl = int(logical_expires_at - now) + 300
            physical_ttl = max(physical_ttl, 60)  # minimum 60s
            await self.client.set(key, serialized_data, ex=physical_ttl)
        else:
            # Safety net: even "no expiry" keys get a 24h TTL to prevent unbounded growth
            await self.client.set(key, serialized_data, ex=86400)

    # ──────────────────────────────────────────────
    # GET: Lấy dữ liệu + xác thực tag versions
    # ──────────────────────────────────────────────

    async def get_or_set_async[T](
        self,
        key: str,
        async_func: Callable[[], Awaitable[T]],
        tags: Sequence[str] | None = None,
        expires: int | datetime | None = 600,
        model_class: type[T] | None = None,
        **kwargs,
    ) -> T:
        now = datetime.now().timestamp()

        logical_expires_at = None
        if expires is not None:
            if isinstance(expires, datetime):
                logical_expires_at = expires.timestamp()
            else:
                logical_expires_at = now + expires

        raw_envelope = await self.client.get(key)

        if raw_envelope is not None:
            try:
                envelope = orjson.loads(raw_envelope)

                if isinstance(envelope, dict) and "value" in envelope:
                    cached_value = envelope["value"]
                    exp_at = envelope.get("logical_expires_at")
                    saved_tags = envelope.get("tags", {})

                    # Bước 1: Kiểm tra thời gian hết hạn logic
                    time_valid = exp_at is None or now < exp_at

                    # Bước 2: Kiểm tra tag versions (Logical Invalidation)
                    tags_valid = (
                        await self._validate_tag_versions(saved_tags)
                        if saved_tags
                        else True
                    )

                    if time_valid and tags_valid:
                        # Cache HIT - dữ liệu còn hợp lệ
                        if (
                            model_class
                            and issubclass(model_class, BaseModel)
                            and isinstance(cached_value, dict)
                        ):
                            return model_class(**cast(dict[str, Any], cached_value))
                        return cast(T, cached_value)

                    # Cache MISS (hết hạn thời gian hoặc tag version thay đổi)
                    # -> Gọi DB để lấy dữ liệu mới
                    try:
                        new_data = await async_func()
                        await self._set_envelope(
                            key, new_data, logical_expires_at, tags, **kwargs
                        )
                        if model_class and issubclass(model_class, BaseModel):
                            if isinstance(new_data, dict):
                                return model_class(**cast(dict[str, Any], new_data))
                            if hasattr(new_data, "_mapping"):
                                return model_class(
                                    **cast(
                                        dict[str, Any],
                                        dict(cast(Any, new_data)._mapping),
                                    )
                                )
                        return new_data
                    except Exception as db_err:
                        logger.warning(
                            "Gọi DB thất bại (%s). Tự động cứu cánh bằng dữ liệu cache cũ cho key: '%s'",
                            db_err,
                            key,
                        )
                        if (
                            model_class
                            and issubclass(model_class, BaseModel)
                            and isinstance(cached_value, dict)
                        ):
                            return model_class(**cast(dict[str, Any], cached_value))
                        return cast(T, cached_value)

            except (orjson.JSONDecodeError, TypeError):
                pass

        # Không có cache -> gọi DB lần đầu
        try:
            new_data = await async_func()
            await self._set_envelope(key, new_data, logical_expires_at, tags, **kwargs)

            if model_class and issubclass(model_class, BaseModel):
                if isinstance(new_data, dict):
                    return model_class(**cast(dict[str, Any], new_data))
                if hasattr(new_data, "_mapping"):
                    return model_class(
                        **cast(dict[str, Any], dict(cast(Any, new_data)._mapping))
                    )

            return new_data
        except Exception as db_err:
            logger.error("Cả Cache và DB đều thất bại cho key '%s'", key, exc_info=True)
            raise db_err

    # ──────────────────────────────────────────────
    # INVALIDATE: Vô hiệu hóa logic theo tag
    # ──────────────────────────────────────────────

    async def remove_async(self, key: str) -> bool:
        return await self.client.delete(key) > 0

    async def invalidate_tags_async(self, tags: Sequence[str] | str) -> None:
        """Vô hiệu hóa logic toàn bộ cache thuộc về các tag.

        Chỉ cần INCR version của tag. Không SCAN, không DEL.
        Tất cả dữ liệu cũ sẽ tự động bị coi là "lỗi thời" khi đọc,
        và sẽ tự hết hạn theo TTL vật lý.
        """
        if isinstance(tags, str):
            tags = [tags]

        if not tags:
            return

        async with self.client.pipeline(transaction=False) as pipe:
            for tag in tags:
                pipe.incr(f"{self.tag_version_prefix}{tag}")
            await pipe.execute()

    def get_cursor_key(self, prefix: CacheTags, req: CursorPaginationRequest) -> str:
        return f"{prefix}:cursor:{req.search}:{req.filters}:{req.limit}:{req.cursor}:{req.sort_field}:{req.is_desc}:cursor_desc-{req.is_cursor_desc}"

    def get_pagination_key(self, prefix: CacheTags, req: PaginationRequest) -> str:
        return f"pagination-{prefix}:{req.page}:{req.limit}:{req.sort_field}:{req.is_desc}:{req.filters}:{req.search}"


RedisDep = Annotated[RedisServices, Depends()]
