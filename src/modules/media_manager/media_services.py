import asyncio
from typing import Any, cast

from fastapi import UploadFile
from sqlmodel import and_, col, or_
from uuid6 import uuid8

from database.models.app_db import SessionDep, SessionFactoryDep
from database.models.media import Medias
from src.modules.setting.setting_services import AppSettingServicesDep
from src.shared.base import BaseCrud, BaseResponse
from src.shared.constants.cache_tags import CacheTags
from src.shared.schemas.pagination_schemas import (
    CursorPaginationRequest,
    CursorPaginationResponse,
)
from src.shared.services.redis_services import RedisDep
from src.shared.services.vercel_blob import VercelBlobDep

from .media_constants import MediaType
from .media_schemas import CreateMediaSchema, MediaMetaData, MediaSchema, UpdateMedia
from .media_select import MediaSelect, PrefixSelect, ValidateNameSelect


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

    def get_file_metadata(self, file: UploadFile) -> MediaMetaData | None:
        if not file.content_type:
            return None

        file_type, file_extension = file.content_type.split("/")
        result = MediaMetaData(sizes=file.size or 0, format=file_extension)

        match file_type:
            case MediaType.IMAGE:
                result.type = MediaType.IMAGE
            case MediaType.VIDEO:
                result.type = MediaType.VIDEO
            case MediaType.AUDIO:
                result.type = MediaType.AUDIO
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
            return await crud.find_by_id(id=id, soft_delete=is_soft_delete)

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

    async def get_breadcrumbs(self, prefix_str: str) -> list[dict[str, Any]]:
        if not prefix_str:
            return []

        # 1. Biến chuỗi "1/2/5/" thành list [1, 2, 5]
        folder_ids = [int(x) for x in prefix_str.split("/") if x]

        folders_data = (
            await self.crud.select(PrefixSelect)
            .where(col(Medias.id).in_(folder_ids))
            .find_many(soft_delete=False)
        )

        # 3. Sắp xếp lại đúng thứ tự của chuỗi prefix ban đầu
        folder_map = {f.id: f.name for f in folders_data}

        breadcrumbs = [
            {"id": f_id, "name": folder_map.get(f_id, "Unknown")}
            for f_id in folder_ids
            if f_id in folder_map
        ]

        return breadcrumbs

    async def list_items_by_folder_cursor_raw(
        self,
        parent_id: int | None,
        payload: CursorPaginationRequest,
        deleted_media: bool = False,
        type_filter: str | None = None,
    ) -> CursorPaginationResponse | None:

        cache_key = (
            self.redis.get_cursor_key(CacheTags.MEDIA, payload)
            + f":parent-{parent_id}:deleted_media-{deleted_media}"
            + f":type-{type_filter}"
        )

        async def get_cursor() -> CursorPaginationResponse:
            query_builder = self.crud.select(MediaSelect)

            # ============================================================
            # 1. XỬ LÝ LOGIC LỌC THEO TRẠNG THÁI XÓA (THÙNG RÁC VS BÌNH THƯỜNG)
            # ============================================================
            if deleted_media:
                if parent_id is None:
                    # TRƯỜNG HỢP A: Sảnh chính Thùng rác
                    # Lấy TẤT CẢ mục bị xóa trực tiếp trên toàn hệ thống (bỏ qua parent_id)
                    query_builder = query_builder.where(
                        and_(
                            col(Medias.deleted_at).is_not(None),
                            Medias.is_direct_delete == True,
                        )
                    )
                else:
                    # TRƯỜNG HỢP B: Người dùng click vào xem nội dung bên trong 1 folder đã xóa
                    # Lấy tất cả các mục con thuộc folder cha này (cả trực tiếp lẫn gián tiếp)
                    query_builder = query_builder.where(
                        and_(
                            Medias.parent_id == parent_id,
                            col(Medias.deleted_at).is_not(None),
                        )
                    )
            else:
                # TRƯỜNG HỢP C: Duyệt file bình thường (Không hiển thị hàng trong thùng rác)
                if parent_id:
                    query_builder = query_builder.where(Medias.parent_id == parent_id)
                else:
                    query_builder = query_builder.where(Medias.parent_id == None)

            # ============================================================
            # 2. XỬ LÝ LOGIC LỌC THEO ĐỊNH DẠNG FILE (TYPE FILTER)
            # ============================================================
            if type_filter:
                if type_filter == "folder":
                    query_builder = query_builder.where(Medias.is_folder)
                elif type_filter in {"image", "video", "audio", "document", "other"}:
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
                soft_delete=not deleted_media,
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
        deleted_media: bool = False,
        type_filter: str | None = None,
    ) -> BaseResponse[CursorPaginationResponse]:
        if parent_id:
            exiting_media = await self._existing_media(parent_id)
            if not exiting_media or not exiting_media.is_folder:
                return BaseResponse.not_found(message="Không tìm thấy thư mục")

        result = await self.list_items_by_folder_cursor_raw(
            parent_id, payload, deleted_media, type_filter
        )
        return BaseResponse.ok(
            data=result or CursorPaginationResponse(data=[], next_cursor=None)
        )

    async def get_one_media_raw(
        self, id: int, deleted_media: bool = False
    ) -> MediaSchema | None:

        async def get_media_async():
            self.crud.select(MediaSelect)
            if deleted_media:
                self.crud.where(col(Medias.deleted_at).is_not(None))
            media = await self.crud.find_by_id(id=id, soft_delete=not deleted_media)
            if not media:
                return None
            result = MediaSelect.model_validate(media, from_attributes=True)
            prefix = await self.get_breadcrumbs(media.prefix)

            return MediaSchema(**result.model_dump(exclude={"prefix"}), prefix=prefix)

        return await self.redis.get_or_set_async(
            key=f"{CacheTags.MEDIA}:{id}:{deleted_media}",
            async_func=get_media_async,
            tags=[CacheTags.MEDIA],
            model_class=MediaSchema,
        )

    async def get_one_media(
        self, id: int, deleted_media: bool = True
    ) -> BaseResponse[MediaSchema]:
        media = await self.get_one_media_raw(id, deleted_media)
        if not media:
            return BaseResponse.not_found(message="Không tìm thấy media")
        return BaseResponse.ok(data=media)

    async def create_media_or_fail(self, payload: CreateMediaSchema) -> Medias:
        """Same as `create_media` but returns the raw persisted model instead of
        an already-rendered `BaseResponse` — for callers (e.g. avatar upload in
        `UserServices`) that need the created row itself, not a JSON response.
        `BaseResponse.fail`/`not_found`/`error` still raise on invalid input."""
        # ----------------------------------------------------------------
        # 1. Kiểm tra thư mục cha (nếu có)
        # ----------------------------------------------------------------
        prefix: str = ""
        if payload.folder_id is not None:
            existing_folder = await self.get_one_media_raw(payload.folder_id)
            if not existing_folder or not existing_folder.is_folder:
                return BaseResponse.not_found(message="Không tìm thấy thư mục")

            if existing_folder.prefix is None or len(existing_folder.prefix) == 0:
                prefix = f"{existing_folder.id}/"
            else:
                prefix = (
                    "/".join([f"{f['id']}" for f in existing_folder.prefix])
                    + f"/{existing_folder.id}/"
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

        return new_media

    async def create_media(self, payload: CreateMediaSchema) -> BaseResponse[Medias]:
        new_media = await self.create_media_or_fail(payload)
        return BaseResponse.created(data=new_media)

    async def bulk_delete_media(
        self, ids: list[int], is_soft_delete: bool = True
    ) -> BaseResponse[bool]:

        # 1. Tìm các bản ghi gốc được yêu cầu xóa trực tiếp từ danh sách ids
        target_medias = (
            await self.crud.select(MediaSelect)
            .where(col(Medias.id).in_(ids))
            .find_many(soft_delete=is_soft_delete)
        )

        if not target_medias:
            return BaseResponse.not_found("Không tìm thấy folder hoặc file")

        folders = [m for m in target_medias if m.is_folder]

        media_ids: list[int] = ids
        media_urls: list[str] = []

        def build_cascade_condition(m):
            expressions = [col(m.id).in_(ids)]
            for f in folders:
                child_prefix_base = f"{f.prefix or ''}{f.id}/"
                expressions.append(col(m.prefix).like(f"{child_prefix_base}%"))
            return or_(*expressions) if len(expressions) > 1 else expressions[0]

        # 2. XỬ LÝ LOGIC ĐẦU VÀO CHO TỪNG CHẾ ĐỘ XÓA
        if not is_soft_delete:
            # HARD DELETE
            find_expressions = [col(Medias.id).in_(ids)]
            for f in folders:
                find_expressions.append(
                    col(Medias.prefix).like(f"{f.prefix or ''}{f.id}/%")
                )
            find_condition = (
                or_(*find_expressions)
                if len(find_expressions) > 1
                else find_expressions[0]
            )

            all_medias_to_delete = (
                await self.crud.select(MediaSelect)
                .where(find_condition)
                .find_many(soft_delete=False)
            )

            media_ids = [
                media.id for media in all_medias_to_delete if media.id is not None
            ]
            media_urls = [media.url for media in all_medias_to_delete if media.url]

            delete_condition = lambda m: col(m.id).in_(media_ids)
        else:
            # SOFT DELETE
            delete_condition = build_cascade_condition

        # 3. THỰC THI TRANSACTION
        db_success = False
        async with self.crud.transaction():
            if not is_soft_delete:
                # Giữ nguyên logic Hard Delete của bạn
                delete_media_task = self.crud.delete(
                    condition=delete_condition,
                    soft_delete=False,
                    autocommit=False,
                )
                if media_urls:
                    delete_vercel_task = self.vercel_blob.delete_async(media_urls)
                    db_success, vercel_success = await asyncio.gather(
                        delete_media_task, delete_vercel_task
                    )
                    if not db_success or not vercel_success:
                        return BaseResponse.error(
                            "Xóa dữ liệu database hoặc xóa file thất bại"
                        )
                else:
                    db_success = await delete_media_task
                    if not db_success:
                        return BaseResponse.not_found("Không tìm thấy folder hoặc file")

            else:
                from sqlmodel import update

                from src.shared.helpers.time_extensions import get_now_vn

                now = get_now_vn()

                # Bước A: Cập nhật các file/thư mục con (Bị xóa ké -> is_direct_delete = False)
                if folders:
                    child_expressions = []
                    for f in folders:
                        child_expressions.append(
                            col(Medias.prefix).like(f"{f.prefix or ''}{f.id}/%")
                        )

                    child_condition = (
                        or_(*child_expressions)
                        if len(child_expressions) > 1
                        else child_expressions[0]
                    )

                    update_children_stmt = (
                        update(Medias)
                        .where(child_condition)
                        .values(deleted_at=now, is_direct_delete=False)
                    )
                    await self.session.exec(update_children_stmt)

                # Bước B: Cập nhật các mục được tick chọn trực tiếp -> is_direct_delete = True
                update_targets_stmt = (
                    update(Medias)
                    .where(col(Medias.id).in_(ids))
                    .values(deleted_at=now, is_direct_delete=True)
                )
                await self.session.exec(update_targets_stmt)
                db_success = True

        await self.redis.invalidate_tags_async(CacheTags.MEDIA)
        return BaseResponse.no_content()

    async def delete_media(
        self, id: int, is_soft_delete: bool = True
    ) -> BaseResponse[bool]:
        return await self.bulk_delete_media(ids=[id], is_soft_delete=is_soft_delete)

    async def restore_media(
        self, id: int
    ) -> BaseResponse[
        Medias
    ]:  # 1. Sửa Type Hint từ bool thành Model của bạn (ví dụ: Medias)
        media = await self._existing_media(id, is_soft_delete=False)
        if not media or media.deleted_at is None:
            return BaseResponse.not_found("Không tìm thấy mục đã xóa")

        async with self.crud.transaction():
            # 2. CHỈ tìm và khôi phục mục con NẾU mục hiện tại là THƯ MỤC
            if getattr(media, "is_folder", False):
                from sqlmodel import update

                # Định nghĩa prefix của các con: "prefix_cha/id_cha/%"
                # Dùng `media.prefix or ''` để xử lý an toàn nếu thư mục gốc có prefix là None hoặc rỗng
                child_prefix = f"{media.prefix or ''}{media.id}/%"

                update_media_task = (
                    update(Medias)
                    .where(col(Medias.prefix).like(child_prefix))
                    .values(deleted_at=None, is_direct_delete=False)
                )
                await self.session.exec(update_media_task)

            # 3. Khôi phục chính bản ghi hiện tại
            media.deleted_at = None
            self.session.add(media)

            # Lưu ý: Nếu block `async with self.crud.transaction():` của bạn đã tự động commit khi hết block,
            # bạn có thể bỏ dòng commit thủ công dưới đây để tránh trùng lặp.
            await self.session.commit()

        # 4. Xóa cache Redis sau khi DB đã thay đổi thành công
        await self.redis.invalidate_tags_async(CacheTags.MEDIA)
        return BaseResponse.ok(data=media)

    async def empty_trash(self) -> BaseResponse[bool]:
        from sqlmodel import select

        self.crud.statement = select(Medias.id)
        ids = await self.crud.where(col(Medias.deleted_at).is_not(None)).find_many(
            soft_delete=False
        )
        if not ids:
            return BaseResponse.fail("Không có rác để xoá!")

        return await self.bulk_delete_media(
            ids=cast(list[int], ids), is_soft_delete=False
        )

    async def update_media(self, id: int, payload: UpdateMedia) -> BaseResponse[Medias]:
        # 1. Kiểm tra sự tồn tại của file/folder hiện tại
        existing_media = await self._existing_media(id, is_soft_delete=False)
        if not existing_media:
            return BaseResponse.not_found("Không tìm thấy folder hoặc file")

        if existing_media.deleted_at is not None:
            return BaseResponse.fail(
                f"Vui lòng khôi phục {'thư mục' if existing_media.is_folder else 'file'} trước khi cập nhật"
            )

        # 2. Kiểm tra trùng tên trùng đường dẫn
        valid_name = await self._validate_unique_name(
            name=payload.name or existing_media.name,
            parent_id=payload.folder_id,
            is_folder=existing_media.is_folder,
        )

        if not valid_name:
            return BaseResponse.fail("Tên đã tồn tại")

        # Lưu lại chuỗi nhận diện gốc của các con cháu TRƯỚC KHI THAY ĐỔI
        old_child_prefix_base = f"{existing_media.prefix}{existing_media.id}/"
        new_child_prefix_base = old_child_prefix_base

        # Khởi tạo một dict chứa các trường cần update cho bản ghi hiện tại
        update_data = {}

        # Thêm name vào dict nếu có thay đổi
        if payload.name:
            update_data["name"] = payload.name

        # Xử lý logic di chuyển thư mục cha nếu có truyền folder_id
        if (
            payload.folder_id is not None
            and existing_media.parent_id != payload.folder_id
        ):
            # folder_id = -1 quy ước là đưa về thư mục gốc
            if payload.folder_id == -1:
                # Nếu đã ở thư mục gốc thì không cần làm gì
                if existing_media.parent_id is not None:
                    update_data["parent_id"] = None
                    new_prefix = ""
                    update_data["prefix"] = new_prefix
                    new_child_prefix_base = f"{existing_media.id}/"
            else:
                if payload.folder_id == existing_media.id:
                    return BaseResponse.fail("Không thể di chuyển thư mục vào chính nó")

                parent_media = await self._existing_media(
                    payload.folder_id, is_soft_delete=False
                )

                if not parent_media or not parent_media.is_folder:
                    return BaseResponse.not_found("Thư mục đích không tồn tại")

                if parent_media.prefix.startswith(old_child_prefix_base):
                    return BaseResponse.fail(
                        "Không thể di chuyển thư mục vào thư mục con của nó"
                    )

                # Đưa các thông tin thay đổi cấu trúc cây vào dict update
                update_data["parent_id"] = payload.folder_id
                new_prefix = f"{parent_media.prefix}{parent_media.id}/"
                update_data["prefix"] = new_prefix

                # Cập nhật lại chuỗi nhận diện mới cho đám con cháu
                new_child_prefix_base = f"{new_prefix}{existing_media.id}/"

        # ======================================================================
        # 3. GỌI HÀM UPDATE CỦA BASECRUD (self.crud.update)
        # Truyền autocommit=False để giữ chung Transaction với câu lệnh Bulk Update phía dưới
        # ======================================================================
        updated_media = await self.crud.update(
            id=id,
            data=update_data,
            soft_delete=False,  # Đã check thủ công ở đầu hàm nên truyền False để tối ưu câu lệnh WHERE
            autocommit=False,
        )

        # Nếu payload trống hoặc không có gì thay đổi, hàm update của BaseCRUD trả về None
        # Lúc này ta lấy luôn existing_media để làm dữ liệu trả về kết quả
        if updated_media is None:
            updated_media = existing_media

        # 4. Nếu là folder và có sự thay đổi đường dẫn (prefix), tiến hành bulk update cho đám con cháu
        if existing_media.is_folder and old_child_prefix_base != new_child_prefix_base:
            from sqlmodel import func, update as sqlmodel_update

            stmt = (
                sqlmodel_update(Medias)
                .where(col(Medias.prefix).like(f"{old_child_prefix_base}%"))
                .values(
                    prefix=func.replace(
                        Medias.prefix,
                        old_child_prefix_base,
                        new_child_prefix_base,
                    )
                )
            )
            await self.session.exec(stmt)

        # 5. Kết thúc toàn bộ tiến trình -> Commit dữ liệu của cả cha lẫn con xuống DB
        await self.session.commit()
        await self.session.refresh(updated_media)
        await self.redis.invalidate_tags_async(CacheTags.MEDIA)
        return BaseResponse.ok(updated_media)
