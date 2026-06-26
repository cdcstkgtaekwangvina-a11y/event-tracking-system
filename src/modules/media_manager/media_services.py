import asyncio
from typing import Optional, Any, cast
from fastapi import UploadFile
from database.models.app_db import SessionDep, SessionFactoryDep
from database.models.media import Medias
from sqlmodel import and_, col
from src.shared.base import BaseCrud, BaseResponse
from src.shared.services.vercel_blob import VercelBlobDep
from .media_select import ValidateNameSelect, MediaSelect
from src.shared.schemas.pagination_schemas import (
    CursorPaginationRequest,
    CursorPaginationResponse,
)
from src.modules.setting.setting_services import AppSettingServicesDep
from .media_schemas import CreateMediaSchema, MediaMetaData, PrefixNode
from .media_constants import MediaType
from uuid import uuid8
from src.shared.services.redis_services import RedisDep
from src.shared.constants.cache_tags import CacheTags


class MediaServices:
    def __init__(
        self,
        session: SessionDep,
        session_factory: SessionFactoryDep,
        vercel_blob: VercelBlobDep,
        app_setting: AppSettingServicesDep,
        redis: RedisDep,
    ):
        self.session = session
        self.crud = BaseCrud(session, Medias)
        self.vercel_blob = vercel_blob
        self.session_factory = session_factory
        self.app_setting = app_setting
        self.redis = redis

    # Validation helpers

    def get_file_metadata(self, file: UploadFile) -> Optional[MediaMetaData]:
        if not file.content_type:
            return None

        file_type, file_extension = file.content_type.split("/")
        result = MediaMetaData(sizes=file.size or 0, format=file_extension)

        match file_type:
            case MediaType.IMAGE:
                result.type = MediaType.IMAGE
            case MediaType.VIDEO:
                result.type = MediaType.VIDEO

            case _:
                content_subtypes = [
                    # 1. Tài liệu Microsoft Office (Hiện đại)
                    "vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "vnd.openxmlformats-officedocument.presentationml.presentation",
                    # 2. Tài liệu Microsoft Office (Cũ)
                    "msword",
                    "vnd.ms-excel",
                    "vnd.ms-powerpoint",
                    "vnd.visio",
                    # 3. Văn bản & Tài liệu phổ biến
                    "pdf",
                    "plain",
                    "rtf",
                    "csv",
                    # 4. Web & Mã nguồn
                    "html",
                    "xml",
                    "markdown",
                    "json",
                ]

                if file_extension in content_subtypes:
                    result.type = MediaType.DOCUMENT
                else:
                    result.type = MediaType.OTHER
        return result

    async def _existing_media(self, id: int, is_soft_delete: bool = True):
        async with self.session_factory() as session:
            crud = BaseCrud(session=session, model=Medias)
            return (
                await crud.select(ValidateNameSelect)
                .where(Medias.id == id)
                .find_one(soft_delete=is_soft_delete)
            )

    async def _validate_unique_name(
        self,
        name: str,
        parent_id: int | None,
        is_folder: bool,
    ) -> bool:

        async with self.session_factory() as session:
            crud = BaseCrud(session=session, model=Medias)
            return not (
                await crud.select(ValidateNameSelect)
                .where(
                    and_(
                        Medias.name == name,
                        Medias.parent_id == parent_id,
                        Medias.is_folder == is_folder,
                    )
                )
                .any_async()
            )

    async def list_items_by_folder_cursor_raw(
        self,
        parent_id: int | None,
        payload: CursorPaginationRequest,
        is_soft_delete: bool = True,
        type_filter: str | None = None,
    ) -> CursorPaginationResponse | None:

        cache_key = (
            self.redis.get_cursor_key(CacheTags.MEDIA, payload)
            + f":parent-{parent_id}:soft_delete-{is_soft_delete}"
            + f":type-{type_filter}"
        )

        async def get_cursor() -> CursorPaginationResponse:
            query_builder = self.crud.select(MediaSelect)

            if parent_id:
                query_builder = query_builder.where(Medias.parent_id == parent_id)
            else:
                query_builder = query_builder.where(Medias.parent_id == None)

            if type_filter:
                if type_filter == "folder":
                    query_builder = query_builder.where(Medias.is_folder)
                elif type_filter in {"image", "video", "document", "other"}:
                    query_builder = query_builder.where(
                        and_(
                            Medias.is_folder == False,
                            cast(Any, Medias.media_metadata)["type"].astext
                            == type_filter,
                        )
                    )

            return await query_builder.cursor_pagination_async(
                payload,
                cursor_field=MediaSelect.nameof(lambda x: x.updated_at),
                search_fields=[MediaSelect.nameof(lambda m: m.name)],
                soft_delete=is_soft_delete,
            )

        return await self.redis.get_or_set_async(
            key=cache_key,
            async_func=get_cursor,
            tags=[CacheTags.MEDIA],
            model_class=CursorPaginationResponse,
        )

    async def list_items_by_folder_cursor(
        self,
        parent_id: int | None,
        payload: CursorPaginationRequest,
        is_soft_delete: bool = True,
        type_filter: str | None = None,
    ) -> BaseResponse[CursorPaginationResponse]:
        if parent_id:
            exiting_media = await self._existing_media(parent_id)
            if not exiting_media or not exiting_media.is_folder:
                return BaseResponse.not_found(message="Không tìm thấy thư mục")

        result = await self.list_items_by_folder_cursor_raw(
            parent_id, payload, is_soft_delete, type_filter
        )
        return BaseResponse.ok(
            data=result or CursorPaginationResponse(data=[], next_cursor=None)
        )

    async def get_one_media_raw(
        self, id: int, is_soft_delete: bool = True
    ) -> Optional[Medias]:
        return await self.redis.get_or_set_async(
            key=f"{CacheTags.MEDIA}:{id}",
            async_func=lambda: self.crud.select(MediaSelect).find_by_id(
                id=id, soft_delete=is_soft_delete
            ),
            tags=[CacheTags.MEDIA],
            model_class=Medias,
        )

    async def get_one_media(
        self, id: int, is_soft_delete: bool = True
    ) -> BaseResponse[MediaSelect]:
        media = await self.get_one_media_raw(id, is_soft_delete)
        if not media:
            return BaseResponse.not_found(message="Không tìm thấy media")
        return BaseResponse.ok(data=MediaSelect(**media.model_dump()))

    async def create_media(self, payload: CreateMediaSchema) -> BaseResponse[Medias]:
        # ----------------------------------------------------------------
        # 1. Kiểm tra thư mục cha (nếu có)
        # ----------------------------------------------------------------
        prefix: list[dict[str, Any]] | None = None
        if payload.folder_id is not None:
            existing_folder = await self.get_one_media_raw(payload.folder_id)
            if not existing_folder or not existing_folder.is_folder:
                return BaseResponse.not_found(message="Không tìm thấy thư mục")

            parent_prefix = existing_folder.prefix or []
            prefix = list(parent_prefix)
            prefix.append(
                PrefixNode(
                    id=existing_folder.id, name=existing_folder.name
                ).model_dump()
            )

        extracted_metadata = None

        # ----------------------------------------------------------------
        # 2. Xử lý trích xuất & kiểm tra File trước (Chưa upload)
        # ----------------------------------------------------------------
        if not payload.is_folder:
            from src.modules.setting.setting_constants import AppConfigKey
            from src.modules.setting.setting_schemas import FileConfigSchema

            if not payload.file:
                return BaseResponse.fail("File không được để trống", status_code=400)

            # Kiểm tra dung lượng file
            size_setting = await self.app_setting.get_setting_value(
                AppConfigKey.file_config, model_cls=FileConfigSchema
            )
            if (
                size_setting
                and payload.file.size
                and payload.file.size > size_setting.max_size_file
            ):
                return BaseResponse.fail(
                    "Kích thước file quá lớn", status_code=400, data=size_setting
                )

            # Đọc thông tin metadata từ file gửi lên (Con trỏ file dịch chuyển về cuối)
            media_metadata = self.get_file_metadata(payload.file)
            if not media_metadata:
                return BaseResponse.fail(
                    "Không thể xác định thông tin file", status_code=400
                )

            extracted_metadata = media_metadata.model_dump()

        # ----------------------------------------------------------------
        # 3. Kiểm tra trùng tên trong Database (Đảm bảo an toàn trước khi upload)
        # ----------------------------------------------------------------
        valid_name = await self._validate_unique_name(
            name=payload.name, parent_id=payload.folder_id, is_folder=payload.is_folder
        )

        if not valid_name:
            return BaseResponse.fail("Tên đã tồn tại", status_code=400)

        # ----------------------------------------------------------------
        # 4. Chuẩn bị dữ liệu Model & Map chuẩn cột database (folder_id -> parent_id)
        # ----------------------------------------------------------------
        dump_data = payload.model_dump(exclude={"file", "folder_id"})
        new_media = Medias(
            **dump_data,
            parent_id=payload.folder_id,
            media_metadata=extracted_metadata,
            prefix=prefix,
        )

        # ----------------------------------------------------------------
        # 5. Tiến hành Upload lên Cloud (Chỉ chạy khi mọi validate đã PASS)
        # ----------------------------------------------------------------
        if not payload.is_folder and payload.file:
            # QUAN TRỌNG: Đưa con trỏ file về lại vị trí đầu tiên để Vercel đọc trọn vẹn dữ liệu
            await payload.file.seek(0)

            # Đổi tên file sang chuỗi UUID tránh trùng lặp trên Storage
            unique_filename = f"{uuid8()}_{payload.name}"
            upload_vercel = await self.vercel_blob.put_async(
                file=payload.file, override_name=unique_filename
            )

            if not upload_vercel or not upload_vercel.url:
                return BaseResponse.error("Upload file lên Cloud thất bại")

            # Gán URL nhận được từ Cloud vào Model
            new_media.url = upload_vercel.url

        # ----------------------------------------------------------------
        # 6. Ghi dữ liệu cuối cùng vào Database
        # ----------------------------------------------------------------
        new_media = await self.crud.create(new_media)
        await self.redis.invalidate_tags_async(CacheTags.MEDIA)

        return BaseResponse.ok(data=new_media)

    async def bulk_delete_media(
        self, ids: list[int], is_soft_delete: bool = True
    ) -> BaseResponse[bool]:

        # 1. Mặc định dùng luôn list ids truyền vào cho việc xóa
        media_ids: list[int] = ids
        media_urls: list[str] = []

        # Chỉ khi HARD DELETE mới cần đi tìm dữ liệu cũ để lấy URL xóa file vật lý
        if not is_soft_delete:
            exiting_medias = (
                await self.crud.select(MediaSelect)
                .where(col(Medias.id).in_(ids))
                .find_many(soft_delete=is_soft_delete)
            )
            if not exiting_medias:
                return BaseResponse.not_found("Không tìm thấy folder hoặc file")

            media_ids = [media.id for media in exiting_medias if media.id is not None]
            media_urls = [media.url for media in exiting_medias if media.url]

        # 2. Thực thi Transaction an toàn
        db_success = False
        try:
            async with self.crud.transaction():
                # Chuẩn bị tác vụ DB (chưa await)
                delete_media_task = self.crud.delete(
                    condition=lambda m: col(m.id).in_(media_ids),
                    soft_delete=is_soft_delete,
                    autocommit=False,
                )

                if media_urls:
                    # Chuẩn bị tác vụ Vercel SDK
                    delete_vercel_task = self.vercel_blob.delete_async(media_urls)

                    # Chạy song song
                    db_success, vercel_success = await asyncio.gather(
                        delete_media_task, delete_vercel_task
                    )

                    # Nếu 1 trong 2 tác vụ thất bại, chủ động raise lỗi để kích hoạt ROLLBACK tự động
                    if not db_success or not vercel_success:
                        raise Exception(
                            "Xóa dữ liệu database hoặc xóa file trên Vercel thất bại"
                        )
                else:
                    # Nếu chỉ xóa mềm (hoặc không có url file), chỉ cần chạy tác vụ DB
                    db_success = await delete_media_task
                    if not db_success:
                        # Trả về luôn từ trong block này là an toàn (không đổi dữ liệu gì nên commit vô hại)
                        return BaseResponse.not_found("Không tìm thấy folder hoặc file")

        except Exception as e:
            return BaseResponse.error(f"Quá trình xóa thất bại: {str(e)}")

        await self.redis.invalidate_tags_async(CacheTags.MEDIA)

        return BaseResponse.no_content()

    async def delete_media(
        self, id: int, is_soft_delete: bool = True
    ) -> BaseResponse[bool]:

        return await self.bulk_delete_media(ids=[id], is_soft_delete=is_soft_delete)
