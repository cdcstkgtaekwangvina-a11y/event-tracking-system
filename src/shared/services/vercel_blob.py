import os
from collections.abc import Iterable
from typing import Annotated, Literal, cast

from dotenv import load_dotenv
from fastapi import Depends, UploadFile
from vercel.blob import AsyncBlobClient, GetBlobResult, ListBlobResult, PutBlobResult

load_dotenv()


class VercelBlobServices:
    def __init__(self):
        self._client = None
        self.access: Literal["public", "private"] = cast(
            Literal["public", "private"], os.getenv("VERCEL_BLOB_ACCESS") or "public"
        )

    @property
    def client(self) -> AsyncBlobClient:
        if self._client is None:
            token: str = os.environ["VERCEL_BLOB_SECRET"]
            self._client = AsyncBlobClient(token=token)
        return self._client

    async def put_async(
        self,
        file: UploadFile,
        override_name: str | None = None,
        folder: str | None = None,
    ) -> PutBlobResult:
        path: str = override_name or file.filename or ""
        if folder:
            path = folder + path
        return await self.client.put(
            path=path,
            body=await file.read(),
            access=self.access,
            content_type=file.content_type,
            overwrite=True,
        )

    async def replace_file_binary(self, file: UploadFile, path: str) -> PutBlobResult:
        return await self.client.put(path, body=await file.read(), access=self.access)

    async def get_async(self, path: str) -> GetBlobResult:
        return await self.client.get(path, access=self.access)

    async def list_objects_async(
        self,
        limit: int | None = 20,
        prefix: str | None = None,
        cursor: str | None = None,
        mode: Literal["expanded", "folded"] = "expanded",
    ) -> ListBlobResult:
        return await self.client.list_objects(
            limit=limit, prefix=prefix, cursor=cursor, mode=mode
        )

    async def delete_async(self, path: str | Iterable[str]) -> bool:
        try:
            if isinstance(path, str):
                urls_to_delete: Iterable[str] = [path]
            else:
                urls_to_delete = path

            await self.client.delete(urls_to_delete)
            return True
        except Exception as e:
            print(f"Xóa blob thất bại: {e}")
            return False


VercelBlobDep = Annotated[VercelBlobServices, Depends()]
