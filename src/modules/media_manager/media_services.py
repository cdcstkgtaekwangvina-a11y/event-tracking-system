from database.models.app_db import SessionDep
from database.models.files import Files
from database.models.folders import Folders
from sqlmodel import select, or_
from sqlalchemy import desc, asc
from typing import cast, Any, List
from src.shared.base import BaseCrud, BaseResponse
from src.shared.schemas.pagination_schemas import (
    PaginationRequest,
    PaginationResponse,
)
from src.shared.services.vercel_blob import VercelBlobDep
from src.modules.media_manager.media_schemas import (
    FileUpdate,
    FolderCreate,
    FolderUpdate,
    FileCreate,
    FolderCursorNode,
    FileCursorNode,
    FolderTreeNode,
)
from src.shared.schemas.pagination_schemas import (
    CursorPaginationRequest,
    CursorPaginationResponse,
)
from datetime import datetime, timezone


class MediaServices:
    def __init__(self, session: SessionDep, vercel_blob: VercelBlobDep):
        self.session = session
        self.file_crud = BaseCrud(session, Files)
        self.folder_crud = BaseCrud(session, Folders)
        self.vercel_blob = vercel_blob

    # Validation helpers

    async def _validate_file_unique_name(
        self, name: str, folder_id: int | None, exclude_id: int | None = None
    ) -> bool:
        stmt = select(Files).where(Files.name == name, Files.folder_id == folder_id)
        if exclude_id is not None:
            stmt = stmt.where(Files.id != exclude_id)
        result = await self.session.exec(stmt)
        return result.first() is not None

    async def _validate_folder_unique_name(
        self, name: str, parent_id: int | None, exclude_id: int | None = None
    ) -> bool:
        stmt = select(Folders).where(
            Folders.name == name, Folders.parent_id == parent_id
        )
        if exclude_id is not None:
            stmt = stmt.where(Folders.id != exclude_id)
        result = await self.session.exec(stmt)
        return result.first() is not None

    # Files

    async def create_file(self, data: FileCreate) -> BaseResponse[Files]:
        if await self._validate_file_unique_name(
            data.file.filename or "", data.folder_id
        ):
            return BaseResponse.fail(
                message="Tên file đã tồn tại trong thư mục này",
                status_code=400,
            )

        upload_result = await self.vercel_blob.put_async(
            file=data.file, folder="media/"
        )

        db_obj = Files(
            name=data.file.filename or "",
            url=upload_result.url,
            type=data.file.content_type or "",
            sizes=data.file.size,
            folder_id=data.folder_id,
        )
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return BaseResponse.created(db_obj, message="Tạo file thành công")

    async def update_file(self, file_id: int, data: FileUpdate) -> BaseResponse[Files]:
        db_obj = await self.file_crud.find_by_id(file_id)
        if db_obj is None:
            return BaseResponse.not_found(message="Không tìm thấy file")

        update_dict = data.model_dump(exclude_unset=True)

        new_name = update_dict.get("name", db_obj.name)
        new_folder_id = update_dict.get("folder_id", db_obj.folder_id)
        if new_name != db_obj.name or new_folder_id != db_obj.folder_id:
            if await self._validate_file_unique_name(
                new_name, new_folder_id, exclude_id=file_id
            ):
                return BaseResponse.fail(
                    message="Tên file đã tồn tại trong thư mục này",
                    status_code=400,
                )

        old_url = db_obj.url
        if data.file is not None:
            upload_result = await self.vercel_blob.put_async(
                file=data.file, folder="media/"
            )
            db_obj.url = upload_result.url
            db_obj.type = data.file.content_type or db_obj.type
            db_obj.sizes = data.file.size or db_obj.sizes

            if old_url:
                await self.vercel_blob.delete_async(old_url)

        for key, value in update_dict.items():
            if key == "file":
                continue
            setattr(db_obj, key, value)

        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return BaseResponse.ok(db_obj, message="Cập nhật file thành công")

    async def delete_file(self, file_id: int) -> BaseResponse[None]:
        db_obj = await self.file_crud.find_by_id(file_id)
        if db_obj is None:
            return BaseResponse.not_found(message="Không tìm thấy file")

        file_url = db_obj.url
        if file_url:
            await self.vercel_blob.delete_async(file_url)

        await self.session.delete(db_obj)
        await self.session.commit()
        return BaseResponse.ok(message="Xóa file thành công")

    async def read_one_file(self, file_id: int) -> BaseResponse[Files]:
        db_obj = await self.file_crud.find_by_id(file_id)
        if db_obj is None:
            return BaseResponse.not_found(message="Không tìm thấy file")
        return BaseResponse.ok(db_obj, message="Lấy chi tiết file thành công")

    async def pagination_files(
        self, pagination: PaginationRequest
    ) -> BaseResponse[PaginationResponse]:
        result = await self.file_crud.pagination_async(pagination)
        return BaseResponse.ok(result, message="Lấy danh sách file thành công")

    # Folders

    async def create_folder(self, data: FolderCreate) -> BaseResponse[Folders]:
        if await self._validate_folder_unique_name(data.name, data.parent_id):
            return BaseResponse.fail(
                message="Tên thư mục đã tồn tại trong thư mục cha này",
                status_code=400,
            )

        db_obj = Folders(**data.model_dump())
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return BaseResponse.created(db_obj, message="Tạo thư mục thành công")

    async def update_folder(
        self, folder_id: int, data: FolderUpdate
    ) -> BaseResponse[Folders]:
        db_obj = await self.folder_crud.find_by_id(folder_id)
        if db_obj is None:
            return BaseResponse.not_found(message="Không tìm thấy thư mục")

        update_dict = data.model_dump(exclude_unset=True)

        new_name = update_dict.get("name", db_obj.name)
        new_parent_id = update_dict.get("parent_id", db_obj.parent_id)
        if new_name != db_obj.name or new_parent_id != db_obj.parent_id:
            if await self._validate_folder_unique_name(
                new_name, new_parent_id, exclude_id=folder_id
            ):
                return BaseResponse.fail(
                    message="Tên thư mục đã tồn tại trong thư mục cha này",
                    status_code=400,
                )

        for key, value in update_dict.items():
            setattr(db_obj, key, value)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return BaseResponse.ok(db_obj, message="Cập nhật thư mục thành công")

    async def delete_folder(self, folder_id: int) -> BaseResponse[None]:
        db_obj = await self.folder_crud.find_by_id(folder_id)
        if db_obj is None:
            return BaseResponse.not_found(message="Không tìm thấy thư mục")
        await self.session.delete(db_obj)
        await self.session.commit()
        return BaseResponse.ok(message="Xóa thư mục thành công")

    async def read_one_folder(self, folder_id: int) -> BaseResponse[Folders]:
        db_obj = await self.folder_crud.find_by_id(folder_id)
        if db_obj is None:
            return BaseResponse.not_found(message="Không tìm thấy thư mục")
        return BaseResponse.ok(db_obj, message="Lấy chi tiết thư mục thành công")

    async def pagination_folders(
        self, pagination: PaginationRequest
    ) -> BaseResponse[PaginationResponse]:
        result = await self.folder_crud.pagination_async(pagination)
        return BaseResponse.ok(result, message="Lấy danh sách thư mục thành công")

    # Cursor pagination: hiển thị file + folder gọn như file manager

    async def list_items_by_folder_cursor(
        self, folder_id: int | None, payload: CursorPaginationRequest
    ) -> BaseResponse[CursorPaginationResponse]:
        cursor_time: datetime | None = None
        cursor_id: int | None = None
        if payload.cursor:
            try:
                parts = payload.cursor.split("_")
                cursor_time = datetime.fromisoformat(parts[0])
                cursor_id = int(parts[1]) if len(parts) > 1 else None
            except Exception:
                cursor_time = None
                cursor_id = None

        file_stmt = cast(Any, select(Files)).where(
            Files.deleted_at == None, Files.folder_id == folder_id
        )
        folder_stmt = cast(Any, select(Folders)).where(
            Folders.deleted_at == None, Folders.parent_id == folder_id
        )

        stmt_f: Any = file_stmt
        stmt_d: Any = folder_stmt

        updated_at_file = cast(Any, Files.updated_at)
        updated_at_folder = cast(Any, Folders.updated_at)
        id_file = cast(Any, Files.id)
        id_folder = cast(Any, Folders.id)

        if payload.is_desc:
            stmt_f = stmt_f.order_by(desc(updated_at_file))
            stmt_d = stmt_d.order_by(desc(updated_at_folder))
        else:
            stmt_f = stmt_f.order_by(asc(updated_at_file))
            stmt_d = stmt_d.order_by(asc(updated_at_folder))

        if cursor_time is not None and cursor_id is not None:
            if payload.is_desc:
                stmt_f = stmt_f.where(
                    or_(
                        updated_at_file < cursor_time,
                        updated_at_file == cursor_time,
                        id_file < cursor_id,
                    )
                )
                stmt_d = stmt_d.where(
                    or_(
                        updated_at_folder < cursor_time,
                        updated_at_folder == cursor_time,
                        id_folder < cursor_id,
                    )
                )
            else:
                stmt_f = stmt_f.where(
                    or_(
                        updated_at_file > cursor_time,
                        updated_at_file == cursor_time,
                        id_file > cursor_id,
                    )
                )
                stmt_d = stmt_d.where(
                    or_(
                        updated_at_folder > cursor_time,
                        updated_at_folder == cursor_time,
                        id_folder > cursor_id,
                    )
                )

        stmt_f = stmt_f.limit(payload.limit)
        stmt_d = stmt_d.limit(payload.limit)

        files = (await self.session.exec(stmt_f)).all()
        folders = (await self.session.exec(stmt_d)).all()

        file_items = [
            FileCursorNode(
                id=r.id,
                name=r.name,
                url=r.url,
                file_type=r.type,
                sizes=r.sizes,
                folder_id=r.folder_id,
                updated_at=r.updated_at,
            )
            for r in files
        ]
        folder_items = [
            FolderCursorNode(
                id=r.id,
                name=r.name,
                parent_id=r.parent_id,
                updated_at=r.updated_at,
            )
            for r in folders
        ]

        merged = file_items + folder_items
        merged.sort(
            key=lambda x: (x.updated_at or datetime.min, x.id),
            reverse=payload.is_desc,
        )
        merged = merged[: payload.limit]

        next_cursor: str | None = None
        has_more = False
        if merged:
            last = merged[-1]
            updated_at = last.updated_at or datetime.min.replace(tzinfo=timezone.utc)
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            next_cursor = f"{updated_at.isoformat()}_{last.id}"
            has_more = len(files) >= payload.limit or len(folders) >= payload.limit

        return BaseResponse.ok(
            CursorPaginationResponse(
                data=merged,
                next_cursor=next_cursor,
                has_more=has_more,
            ),
            message="Lấy danh sách theo cursor thành công",
        )

    # Folder tree for sidebar navigation
    async def get_folder_tree(
        self, parent_id: int | None = None
    ) -> BaseResponse[List[FolderTreeNode]]:
        # Get all folders (non-deleted)
        stmt = cast(Any, select(Folders)).where(Folders.deleted_at == None)
        folders = (await self.session.exec(stmt)).all()

        # Build tree structure
        folder_map: dict[int, FolderTreeNode] = {}
        for f in folders:
            folder_map[f.id] = FolderTreeNode(
                id=f.id,
                name=f.name,
                parent_id=f.parent_id,
                children=[],
                item_count=0,
            )

        # Count items in each folder
        for f in folders:
            # Count files in this folder
            file_stmt = cast(Any, select(Files)).where(
                Files.deleted_at == None, Files.folder_id == f.id
            )
            file_count = len((await self.session.exec(file_stmt)).all())

            # Count subfolders (direct children)
            subfolder_count = sum(1 for fol in folders if fol.parent_id == f.id)

            if f.id in folder_map:
                folder_map[f.id].item_count = file_count + subfolder_count

        # Build tree
        root_nodes: List[FolderTreeNode] = []
        for f in folders:
            node = folder_map[f.id]
            if f.parent_id is None or f.parent_id == parent_id:
                if parent_id is None or f.parent_id == parent_id:
                    root_nodes.append(node)
            else:
                if f.parent_id in folder_map:
                    folder_map[f.parent_id].children.append(node)

        # Sort children by name
        def sort_tree(nodes: List[FolderTreeNode]):
            for n in nodes:
                if n.children:
                    n.children.sort(key=lambda x: x.name)
                    sort_tree(n.children)

        if parent_id is None:
            # Return full tree from root
            roots = [n for n in root_nodes if n.parent_id is None]
            roots.sort(key=lambda x: x.name)
            sort_tree(roots)
            return BaseResponse.ok(roots, message="Lấy cây thư mục thành công")
        else:
            # Return children of specific parent
            if parent_id in folder_map:
                children = folder_map[parent_id].children
                children.sort(key=lambda x: x.name)
                sort_tree(children)
                return BaseResponse.ok(children, message="Lấy thư mục con thành công")
            return BaseResponse.ok([], message="Lấy thư mục con thành công")
