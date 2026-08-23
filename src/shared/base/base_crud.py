from collections.abc import Callable, Sequence
from contextlib import asynccontextmanager
from inspect import isclass
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Protocol,
    TypeGuard,
    TypeVar,
    cast,
)

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import String, and_, asc, desc, exists, func, or_
from sqlmodel import SQLModel, delete, select, update
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import Select, SelectOfScalar
from typing_extensions import Self, overload

from src.shared.base.base_logger import get_logger
from src.shared.helpers.time_extensions import get_now_vn
from src.shared.schemas.pagination_schemas import (
    CursorPaginationRequest,
    CursorPaginationResponse,
    PaginationRequest,
    PaginationResponse,
)

logger = get_logger(__name__)

if TYPE_CHECKING:
    pass

T = TypeVar("T", bound=SQLModel)
M = TypeVar("M")


class HasIdProtocol(Protocol):
    id: Any


class HasDeletedAtProtocol(Protocol):
    deleted_at: Any


class HasCreatedAtProtocol(Protocol):
    created_at: Any


class HasUpdatedAtProtocol(Protocol):
    updated_at: Any


class BaseCrud(Generic[T]):
    model: type[T]
    session: AsyncSession
    statement: SelectOfScalar[Any] | Select[Any]
    dto_class: type[BaseModel] | None = None

    def __init__(self, session: AsyncSession, model: type[T]):
        self.session = session
        self.model = model
        self.statement = select(model)
        self.dto_class = None

    def is_has_soft_delete(
        self, model: type[M]
    ) -> TypeGuard[type[HasDeletedAtProtocol]]:
        from database.models.base_model import DeletedAtModel

        return isinstance(model, type) and issubclass(model, DeletedAtModel)

    def is_has_primary_key(self, model: type[M]) -> TypeGuard[type[HasIdProtocol]]:
        from database.models.base_model import PrimaryModel

        return isinstance(model, type) and issubclass(model, PrimaryModel)

    def is_has_created_at(
        self, model: type[M]
    ) -> TypeGuard[type[HasCreatedAtProtocol]]:
        from database.models.base_model import CreatedAtModel

        return isinstance(model, type) and issubclass(model, CreatedAtModel)

    def is_has_updated_at(
        self, model: type[M]
    ) -> TypeGuard[type[HasUpdatedAtProtocol]]:
        from database.models.base_model import UpdatedAtModel

        return isinstance(model, type) and issubclass(model, UpdatedAtModel)

    @overload
    def map_dto_class(self, data: T, dto_class: None) -> T: ...

    @overload
    def map_dto_class(self, data: T, dto_class: type[BaseModel]) -> BaseModel: ...

    def map_dto_class(
        self, data: T, dto_class: type[BaseModel] | None
    ) -> T | BaseModel:
        if dto_class:
            return dto_class.model_validate(data, from_attributes=True)
        return data

    # Start Query builder
    @overload
    def select(
        self,
        dto_class: type[BaseModel],
        *,
        logic_column: list[Any] | None = None,
    ) -> Self: ...
    @overload
    def select(self, *columns: Any) -> Self: ...

    def select(
        self, *args: Any, logic_column: list[Any] | None = None, **kwargs: Any
    ) -> Self:
        dto_class_arg = args[0] if args else kwargs.get("dto_class")

        if (
            dto_class_arg
            and isclass(dto_class_arg)
            and issubclass(dto_class_arg, BaseModel)
            and dto_class_arg != self.model
        ):
            self.dto_class = dto_class_arg
            table_class = self.model

            columns = [
                getattr(table_class, f)
                for f in self.dto_class.model_fields.keys()
                if hasattr(table_class, f)
            ]

            if logic_column:
                sanitized_logic = [
                    getattr(table_class, col) if isinstance(col, str) else col
                    for col in logic_column
                    if not isinstance(col, str) or hasattr(table_class, col)
                ]
                columns.extend(sanitized_logic)

            self.statement = select(*columns).select_from(self.model)
        else:
            self.dto_class = None
            self.statement = select(*args).select_from(self.model)

        return self

    def where(self, *conditions: Any) -> Self:
        self.statement = self.statement.where(*conditions)
        return self

    def options(self, *opts: Any) -> Self:
        if self.statement is not None:
            self.statement = self.statement.options(*opts)
        return self

    def order_by(self, *ordering: Any) -> Self:
        self.statement = self.statement.order_by(*ordering)
        return self

    def count(self, *conditions: Any) -> Self:
        if self.statement is not None:
            if conditions:
                self.statement = self.statement.where(*conditions)

            subquery = self.statement.subquery()
            self.statement = select(func.count()).select_from(subquery)

        return self

    def any(self, *conditions: Any) -> Self:
        if self.statement is not None:
            if conditions:
                self.statement = self.statement.where(*conditions)

            self.statement = select(self.statement.exists())

        return self

    def join(
        self,
        target: type[SQLModel] | Any,
        onclause: Any = None,
        isouter: bool = False,
        full: bool = False,
    ) -> Self:
        if self.statement is not None:
            self.statement = self.statement.join(
                target=target, onclause=onclause, isouter=isouter, full=full
            )
        return self

    def group_by(self, *column: Any) -> Self:
        if self.statement is not None:
            self.statement = self.statement.group_by(*column)
        return self

    @asynccontextmanager
    async def transaction(self):
        try:
            yield
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logger.error(e)
            raise e

    # end Query builder
    async def create(self, data, autocommit: bool = True) -> T | None:
        create_data = data.model_dump() if hasattr(data, "model_dump") else data
        db_obj = self.model(**create_data)

        if self.is_has_updated_at(self.model):
            db_obj.updated_at = get_now_vn()

        self.session.add(db_obj)
        await self.session.flush()

        if autocommit:
            await self.session.commit()

        return db_obj

    async def find_one(
        self,
        statement: SelectOfScalar[Any] | Select[Any] | None = None,
        soft_delete: bool = True,
        dto_class: type[BaseModel] | None = None,
    ) -> Any | None:

        if statement is not None:
            self.statement = statement

        if self.is_has_soft_delete(self.model) and soft_delete:
            self.statement = self.statement.where(self.model.deleted_at == None)

        target_dto = dto_class or self.dto_class

        result = await self.session.exec(self.statement)

        row = result.first()

        self.statement = select(self.model)
        self.dto_class = None

        if not row:
            return None

        if target_dto:
            if hasattr(row, "_mapping"):
                return target_dto.model_validate(row._mapping)
            return target_dto.model_validate(row)

        return row

    async def find_by_id(self, id: Any, soft_delete: bool = True) -> T | None:
        statement = self.statement if self.statement is not None else select(self.model)

        m = self.model

        if self.is_has_soft_delete(m) and soft_delete:
            if hasattr(m, "deleted_at"):
                statement = statement.where(m.deleted_at == None)

        if self.is_has_primary_key(self.model):
            statement = statement.where(self.model.id == id)
        else:
            raise HTTPException(
                status_code=500, detail="Model does not have a primary key"
            )

        result = await self.session.exec(statement)
        self.statement = select(self.model)

        return result.first()

    async def find_many(
        self,
        statement: SelectOfScalar[Any] | Select[Any] | None = None,
        soft_delete: bool = True,
    ) -> Sequence[Any]:
        if statement is not None:
            self.statement = statement
        if self.is_has_soft_delete(self.model) and soft_delete:
            self.statement = self.statement.where(self.model.deleted_at == None)
        result = await self.session.exec(self.statement)
        self.statement = select(self.model)
        return result.all()

    async def update(
        self,
        id: Any = None,
        condition: Callable[[Any], Any] | None = None,
        data: Any = None,
        soft_delete: bool = True,
        autocommit: bool = True,
    ) -> T | None:
        # 1. Xử lý dữ liệu update đầu vào
        update_data = (
            data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else data
        )

        if not update_data:
            self.statement = select(self.model)
            return None

        # 2. Kiểm tra và tự động cập nhật trường updated_at nếu có
        if hasattr(self, "is_has_updated_at") and self.is_has_updated_at(self.model):
            update_data["updated_at"] = get_now_vn()

        # 3. Xác định điều kiện WHERE (Ưu tiên id trước, condition sau)
        if id is not None and self.is_has_primary_key(self.model):
            where_clause = self.model.id == id
        elif condition is not None:
            where_clause = condition(self.model)
        else:
            self.statement = select(self.model)
            return None
        stmt = update(self.model).where(where_clause)

        if soft_delete and self.is_has_soft_delete(self.model):
            stmt = stmt.where(self.model.deleted_at == None)

        stmt = stmt.values(**update_data).returning(self.model)

        result = await self.session.exec(stmt)
        db_obj = result.scalar_one_or_none()

        if autocommit:
            await self.session.commit()

        self.statement = select(self.model)
        return db_obj

    async def delete(
        self,
        id: Any = None,
        condition: Callable[[Any], Any] | None = None,
        soft_delete: bool = True,
        autocommit: bool = True,
    ) -> bool:

        if id is not None and self.is_has_primary_key(self.model):
            where_clause = self.model.id == id
        elif condition is not None:
            where_clause = condition(self.model)
        else:
            self.statement = select(self.model)
            return False

        if soft_delete and self.is_has_soft_delete(self.model):
            statement = (
                update(self.model).where(where_clause).values(deleted_at=get_now_vn())
            )
        else:
            statement = delete(self.model).where(where_clause)

        # 3. Thực thi câu lệnh
        result = await self.session.exec(statement)

        if autocommit:
            await self.session.commit()

        # Trả về True nếu có ít nhất một dòng dữ liệu bị ảnh hưởng
        self.statement = select(self.model)
        return result.rowcount > 0

    async def any_async(
        self,
        statement: SelectOfScalar[Any] | Select[Any] | None = None,
        soft_delete: bool = True,
    ) -> bool:
        if statement is None:
            if self.statement is None:
                statement = select(self.model)

        else:
            self.statement = statement
        if self.is_has_soft_delete(self.model) and soft_delete:
            self.statement = self.statement.where(self.model.deleted_at == None)
        stmt = select(exists(self.statement))
        result = await self.session.exec(stmt)
        self.statement = select(self.model)
        return bool(result.first())

    async def count_async(
        self,
        statement: SelectOfScalar[Any] | Select[Any] | None = None,
        soft_delete: bool = True,
    ) -> int:
        if statement is not None:
            self.statement = statement
        if self.statement is None:
            self.statement = select(self.model)
        if self.is_has_soft_delete(self.model) and soft_delete:
            self.statement = self.statement.where(self.model.deleted_at == None)
        count_statement = select(func.count()).select_from(self.statement.subquery())
        result = await self.session.exec(count_statement)
        self.statement = select(self.model)
        return result.one() or 0

    async def pagination_async(
        self,
        pagination: PaginationRequest,
        search_fields: list[str] | None = None,
        search_conditions: list[Any] | None = None,
        soft_delete: bool = True,
    ) -> PaginationResponse:

        if self.statement is None:
            self.statement = select(self.model)

        if self.is_has_soft_delete(self.model) and soft_delete:
            self.statement = self.statement.where(self.model.deleted_at == None)

        # 1. XỬ LÝ FILTERS
        if pagination.filters:
            for f in pagination.filters:
                if f.field:
                    if hasattr(self.model, f.field):
                        column = getattr(self.model, f.field)
                        self.statement = cast(Any, self.statement).where(
                            column == f.value
                        )
                    elif "." in f.field:
                        parts = f.field.split(".", 1)
                        if hasattr(self.model, parts[0]):
                            base_col = getattr(self.model, parts[0])
                            self.statement = cast(Any, self.statement).where(
                                base_col[parts[1]].astext == str(f.value)
                            )

        # 2. XỬ LÝ SEARCH (Đã dọn dẹp logic lặp)
        if pagination.search:
            if search_conditions is None:
                search_conditions = []

            if not search_conditions:
                if search_fields is not None:
                    for field in search_fields:
                        if hasattr(self.model, field):
                            column = getattr(self.model, field)
                            search_conditions.append(
                                func.unaccent(column).ilike(
                                    func.unaccent(f"%{pagination.search}%")
                                )
                            )
                else:
                    table = getattr(self.model, "__table__", None)
                    if table is not None:
                        for column in table.columns:
                            if (
                                isinstance(column.type, String)
                                or column.type.__class__.__name__ == "AutoString"
                            ):
                                search_conditions.append(
                                    func.unaccent(column).ilike(
                                        func.unaccent(f"%{pagination.search}%")
                                    )
                                )

            if search_conditions:
                self.statement = self.statement.where(or_(*search_conditions))

        # 3. ĐẾM TỔNG SỐ BẢN GHI (COUNT)
        count_statement = select(func.count()).select_from(self.statement.subquery())
        total = (await self.session.exec(count_statement)).one() or 0

        # 4. XỬ LÝ ORDER BY (Đã fix lỗi crash tiềm ẩn)
        if pagination.sort_field and hasattr(self.model, pagination.sort_field):
            sort_column = getattr(self.model, pagination.sort_field)
            if pagination.is_desc:
                self.statement = self.statement.order_by(desc(sort_column))
            else:
                self.statement = self.statement.order_by(asc(sort_column))
        else:
            sort_col = None
            if self.is_has_created_at(self.model):
                sort_col = cast(Any, self.model.created_at)
            elif self.is_has_updated_at(self.model):
                sort_col = cast(Any, self.model.updated_at)
            else:
                # Fallback an toàn về khóa chính (id) nếu không có timestamp
                sort_col = cast(Any, getattr(self.model, "id", None))

            if sort_col is not None:
                # Mặc định: mới nhất lên trên (DESC theo created_at)
                self.statement = self.statement.order_by(desc(sort_col))

        # 5. ÁP DỤNG LIMIT & OFFSET
        offset = (pagination.page - 1) * pagination.limit
        self.statement = self.statement.offset(offset).limit(pagination.limit)

        # 6. EXECUTE QUERY VÀ TRẢ KẾT QUẢ
        result = await self.session.exec(self.statement)
        data = result.all()

        if self.dto_class and data:
            data = [
                self.dto_class.model_validate(row, from_attributes=True) for row in data
            ]

        self.statement = select(self.model)
        return PaginationResponse(
            page=pagination.page,
            limit=pagination.limit,
            total=total,
            total_items=total,
            data=list(data) if data else None,
        )

    async def cursor_pagination_async(
        self,
        cursor_request: CursorPaginationRequest,
        cursor_field: str | None = None,
        search_fields: list[str] | None = None,
        search_conditions: list[Any] | None = None,
        soft_delete: bool = True,
    ) -> CursorPaginationResponse:

        if self.statement is None:
            self.statement = select(self.model)

        if self.is_has_soft_delete(self.model) and soft_delete:
            self.statement = self.statement.where(self.model.deleted_at == None)

        # 1. XỬ LÝ FILTER
        if cursor_request.filters:
            for f in cursor_request.filters:
                if f.field:
                    if hasattr(self.model, f.field):
                        column = getattr(self.model, f.field)
                        self.statement = cast(Any, self.statement).where(
                            column == f.value
                        )
                    elif "." in f.field:
                        parts = f.field.split(".", 1)
                        if hasattr(self.model, parts[0]):
                            base_col = getattr(self.model, parts[0])
                            self.statement = cast(Any, self.statement).where(
                                base_col[parts[1]].astext == str(f.value)
                            )

        # 2. XỬ LÝ SEARCH (Đã dọn dẹp logic bị lặp)
        if cursor_request.search:
            if search_conditions is None:
                search_conditions = []

            # Chỉ tự động build điều kiện search nếu danh sách rỗng
            if not search_conditions:
                if search_fields is not None:
                    for field in search_fields:
                        if hasattr(self.model, field):
                            column = getattr(self.model, field)
                            search_conditions.append(
                                func.unaccent(column).ilike(
                                    func.unaccent(f"%{cursor_request.search}%")
                                )
                            )
                else:
                    table = getattr(self.model, "__table__", None)
                    if table is not None:
                        for column in table.columns:
                            if (
                                isinstance(column.type, String)
                                or column.type.__class__.__name__ == "AutoString"
                            ):
                                search_conditions.append(
                                    func.unaccent(column).ilike(
                                        func.unaccent(f"%{cursor_request.search}%")
                                    )
                                )

            if search_conditions:
                self.statement = self.statement.where(or_(*search_conditions))

        stmt = cast(Any, self.statement)
        limit = cursor_request.limit
        is_cursor_desc = cursor_request.is_cursor_desc

        # 3. QUYẾT ĐỊNH TRƯỜNG DỮ LIỆU ĐỂ SORT (LOGIC BẠN YÊU CẦU)
        if cursor_field is None:
            if self.is_has_updated_at(self.model):
                cursor_field = "updated_at"
            else:
                cursor_field = "created_at"

        # Nếu sort_field có giá trị -> dùng sort_field. Nếu null -> dùng cursor_field.
        final_sort_field = getattr(cursor_request, "sort_field", None) or cursor_field

        sort_column = getattr(self.model, final_sort_field, None)

        # Hỗ trợ sort qua JSON field, VD: media_metadata.sizes
        if sort_column is None and final_sort_field and "." in final_sort_field:
            parts = final_sort_field.split(".", 1)
            if hasattr(self.model, parts[0]):
                base_col = getattr(self.model, parts[0])
                from sqlalchemy import Integer

                # Mặc định ép sang Integer để sort kích thước, bạn có thể điều chỉnh sau
                sort_column = base_col[parts[1]].astext.cast(Integer)

        primary_key = cast(Any, getattr(self.model, "id", None))

        # 4. PARSE CURSOR
        cursor_time = None
        cursor_id = None
        if cursor_request.cursor:
            parts = cursor_request.cursor.split("_", 1)
            if len(parts) == 2:
                try:
                    cursor_time_str = parts[0]
                    # Khôi phục dấu + bị mất do URL decode (VD: 2026-06-26 03:04:15 00:00 -> +00:00)
                    if len(cursor_time_str) >= 25 and cursor_time_str.rfind(" ") > 19:
                        last_space = cursor_time_str.rfind(" ")
                        cursor_time_str = (
                            cursor_time_str[:last_space]
                            + "+"
                            + cursor_time_str[last_space + 1 :]
                        )

                    try:
                        from datetime import datetime

                        cursor_time = datetime.fromisoformat(cursor_time_str)
                    except Exception:
                        cursor_time = parts[0]  # Fallback

                    cursor_id = int(parts[1])
                except Exception:
                    pass  # Parse lỗi thì bỏ qua, coi như fetch từ đầu
            else:
                try:
                    cursor_time = parts[0]
                except Exception:
                    pass

        # 5. ÁP DỤNG ORDER BY
        if sort_column is not None and primary_key is not None:
            if is_cursor_desc:
                stmt = stmt.order_by(desc(sort_column), desc(primary_key))
            else:
                stmt = stmt.order_by(asc(sort_column), asc(primary_key))

        # 6. ÁP DỤNG ĐIỀU KIỆN WHERE CHO PAGINATION
        if (
            cursor_id is not None
            and cursor_time is not None
            and primary_key is not None
        ):
            if is_cursor_desc:
                stmt = stmt.where(
                    or_(
                        cast(Any, sort_column) < cursor_time,
                        and_(
                            cast(Any, sort_column) == cursor_time,
                            cast(Any, primary_key) < cursor_id,
                        ),
                    )
                )
            else:
                stmt = stmt.where(
                    or_(
                        cast(Any, sort_column) > cursor_time,
                        and_(
                            cast(Any, sort_column) == cursor_time,
                            cast(Any, primary_key) > cursor_id,
                        ),
                    )
                )

        # 7. EXECUTE QUERY
        stmt = stmt.limit(limit)
        result = await self.session.exec(stmt)
        data = result.all()

        if self.dto_class and data:
            data = [
                self.dto_class.model_validate(row, from_attributes=True) for row in data
            ]

        # 8. SINH NEXT CURSOR
        next_cursor = None
        has_more = False
        if data:
            last = data[-1]
            # Lấy giá trị sort của dòng cuối dựa trên final_sort_field
            last_sort = getattr(last, final_sort_field, None)
            last_id = getattr(last, "id", None)

            sort_val = last_sort if last_sort is not None else ""
            id_val = last_id if last_id is not None else 0

            next_cursor = f"{sort_val}_{id_val}"
            has_more = len(data) >= limit

        self.statement = select(self.model)
        return CursorPaginationResponse(
            data=list(data) if data else None,
            next_cursor=next_cursor,
            has_more=has_more,
        )
