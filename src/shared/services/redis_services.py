import orjson
import logging
import os
from collections.abc import Callable, Awaitable
from datetime import datetime
from typing import Any, Optional, Sequence, cast, Annotated
import redis.asyncio as redis
from dotenv import load_dotenv
from fastapi import Depends
from pydantic import BaseModel

load_dotenv()

logger = logging.getLogger(__name__)


class RedisServices:
    url: str = os.environ["REDIS_URL"]

    def __init__(self):
        pool = redis.ConnectionPool.from_url(
            self.url, max_connections=30, decode_responses=True
        )
        self.client = redis.Redis.from_pool(connection_pool=pool)
        self.tag_prefix = "cache:tag:"

    @staticmethod
    def _orjson_default(obj: Any) -> Any:
        if hasattr(obj, "_mapping"):
            return dict(obj._mapping)
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        if obj.__class__.__name__ == "UUID":
            return str(obj)
        raise TypeError(f"Type {obj.__class__.__name__} not serializable")

    async def _set_envelope(
        self,
        key: str,
        value: Any,
        logical_expires_at: Optional[float],
        tags: Optional[Sequence[str]] = None,
        **kwargs,
    ):
        envelope = {
            "value": value,
            "logical_expires_at": logical_expires_at,
            "tags": tags or [],
        }
        serialized_data = orjson.dumps(envelope, default=self._orjson_default)

        await self.client.set(key, serialized_data)

        if tags:
            for tag in tags:
                tag_key = f"{self.tag_prefix}{tag}"
                await self.client.sadd(tag_key, key)

                await self.client.expire(tag_key, 86400)

    async def get_or_set_async[T](
        self,
        key: str,
        async_func: Callable[[], Awaitable[T]],
        tags: Optional[Sequence[str]] = None,
        expires: Optional[int | datetime] = 600,
        model_class: Optional[type[T]] = None,
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

                    if exp_at is None or now < exp_at:
                        if (
                            model_class
                            and issubclass(model_class, BaseModel)
                            and isinstance(cached_value, dict)
                        ):
                            return model_class(**cast(dict[str, Any], cached_value))
                        return cast(T, cached_value)

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

    async def remove_async(self, key: str) -> bool:
        return await self.client.delete(key) > 0

    async def remove_tags_async(self, tags: Sequence[str] | str) -> bool:
        if isinstance(tags, str):
            tags = [tags]

        if not tags:
            return False

        async with self.client.pipeline(transaction=False) as pipe:
            for tag in tags:
                pipe.smembers(f"{self.tag_prefix}{tag}")
            all_tag_members = await pipe.execute()

        keys_to_delete = set()
        tag_keys_to_delete = []

        for tag, members in zip(tags, all_tag_members):
            if members:
                keys_to_delete.update(members)
                tag_keys_to_delete.append(f"{self.tag_prefix}{tag}")

        if not keys_to_delete and not tag_keys_to_delete:
            return False

        async with self.client.pipeline(transaction=True) as pipe:
            if keys_to_delete:
                pipe.delete(*keys_to_delete)
            if tag_keys_to_delete:
                pipe.delete(*tag_keys_to_delete)
            results = await pipe.execute()

        return sum(results) > 0


RedisDep = Annotated[RedisServices, Depends()]
