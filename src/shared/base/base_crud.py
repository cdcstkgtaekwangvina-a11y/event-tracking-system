from sqlalchemy.exc import SQLAlchemyError
from src.shared.helpers.time_extensions import get_now_vn
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel, select
from sqlmodel.sql.expression import SelectOfScalar, Select
from typing import (
    TypeVar,
    Generic,
    Type,
    Optional,
    TypeGuard,
    Any,
    Sequence,
    cast,
    List,
    TYPE_CHECKING,
    Callable,
)
from sqlalchemy import func, exists, or_, desc, asc, String, update
from fastapi import HTTPException
from src.shared.schemas.pagination_schemas import (
    PaginationRequest,
    PaginationResponse,
    CursorPaginationRequest,
    CursorPaginationResponse,
)
from pydantic import BaseModel
from typing_extensions import Self, overload
from inspect import isclass
import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from database.models.base_model import (
        PrimaryModel,
        CreatedAtModel,
        UpdatedAtModel,
        DeletedAtModel,
    )

T = TypeVar("T", bound=SQLModel)


class BaseCrud(Generic[T]):
    model: Type[T]
    session: AsyncSession
    statement: SelectOfScalar[Any] | Select[Any]
    dto_class: Optional[Type[BaseModel]] = None

    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model
        self.statement = select(model)
        self.dto_class = None

    def is_has_soft_delete(self, model: Type[T]) -> TypeGuard[Type[DeletedAtModel]]:
        from database.models.base_model import DeletedAtModel

        return isinstance(model, type) and issubclass(model, DeletedAtModel)

    def is_has_created_at(self, model: Type[T]) -> TypeGuard[Type[CreatedAtModel]]:
        from database.models.base_model import CreatedAtModel

        return isinstance(model, type) and issubclass(model, CreatedAtModel)

    def is_has_updated_at(self, model: Type[T]) -> TypeGuard[Type[UpdatedAtModel]]:
        from database.models.base_model import UpdatedAtModel

        return isinstance(model, type) and issubclass(model, UpdatedAtModel)

    def is_has_primary_key(self, model: Type[T]) -> TypeGuard[Type[PrimaryModel]]:
        from database.models.base_model import PrimaryModel

        return isinstance(model, type) and issubclass(model, PrimaryModel)

    # Start Query builder
    @overload
    def select(
        self,
        dto_class: type[BaseModel],
        *,
        logic_column: Optional[List[Any]] = None,
    ) -> Self: ...
    @overload
    def select(self, *columns: Any) -> Self: ...

    def select(self, *args: Any, logic_column: Optional[List[Any]] = None) -> Self:
        if len(args) == 1 and isclass(args[0]) and issubclass(args[0], BaseModel):
            self.dto_class = args[0]
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

            self.statement = select(*columns)
        else:
            self.dto_class = None
            self.statement = select(*args)

        return self

    def where(self, *conditions: Any) -> Self:
        self.statement = self.statement.where(*conditions)
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
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(e)
            raise e

    # end Query builder
    async def create(self, data, autocommit: bool = True) -> Optional[T]:
        create_data = data.model_dump() if hasattr(data, "model_dump") else data
        db_obj = self.model(**create_data)

        if self.is_has_updated_at(self.model):
            db_obj.updated_at = get_now_vn()

        self.session.add(db_obj)
        await self.session.flush()

        if autocommit:
            await self.session.commit()

        return db_obj

    async def find_one(self, soft_delete: bool = True) -> Optional[T]:
        if self.is_has_soft_delete(self.model) and soft_delete:
            self.statement = self.statement.where(self.model.deleted_at == None)

        result = await self.session.exec(self.statement)
        return result.first()

    async def find_by_id(self, id: Any, soft_delete: bool = True) -> Optional[T]:
        statement = self.statement if self.statement is not None else select(self.model)

        m = self.model

        if self.is_has_soft_delete(m) and soft_delete:
            statement = statement.where(m.deleted_at == None)

        if self.is_has_primary_key(self.model):
            primary_key_attr = getattr(self.model, "id")
            statement = statement.where(primary_key_attr == id)
        else:
            raise HTTPException(
                status_code=500, detail="Model does not have a primary key"
            )

        result = await self.session.exec(statement)
        self.statement = select(self.model)
        return result.first()

    async def find_many(self, soft_delete: bool = True) -> Sequence[T]:
        if self.statement is None:
            self.statement = select(self.model)
        if self.is_has_soft_delete(self.model) and soft_delete:
            self.statement = self.statement.where(self.model.deleted_at == None)
        result = await self.session.exec(self.statement)
        return result.all()

    async def update(
        self,
        condition: Callable[[Any], Any],
        data: Any,
        soft_delete: bool = True,
        autocommit: bool = True,
    ) -> Optional[T]:
        update_data = (
            data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else data
        )

        if not update_data:
            return None

        if hasattr(self, "is_has_updated_at") and self.is_has_updated_at(self.model):
            update_data["updated_at"] = get_now_vn()

        stmt = update(self.model).where(condition(self.model))

        if soft_delete and self.is_has_soft_delete(self.model):
            stmt = stmt.where(getattr(self.model, "deleted_at") == None)

        stmt = stmt.values(**update_data).returning(self.model)

        result = await self.session.exec(stmt)
        db_obj = result.scalar_one_or_none()

        if autocommit:
            await self.session.commit()
        return db_obj

    async def delete(self, soft_delete: bool = True, autocommit: bool = True) -> bool:
        db_obj = await self.find_one()
        if db_obj is None:
            return False
        if soft_delete:
            db_obj.deleted_at = get_now_vn()
            self.session.add(db_obj)
            if autocommit:
                await self.session.commit()
            return True
        else:
            await self.session.delete(db_obj)
            if autocommit:
                await self.session.commit()
            return True

    async def any_async(self, soft_delete: bool = True) -> bool:
        if self.statement is None:
            self.statement = select(self.model)
        if self.is_has_soft_delete(self.model) and soft_delete:
            self.statement = self.statement.where(self.model.deleted_at == None)
        stmt = select(exists(self.statement))
        result = await self.session.exec(stmt)
        return bool(result.first())

    async def count_async(self, soft_delete: bool = True) -> int:
        if self.statement is None:
            self.statement = select(self.model)
        if self.is_has_soft_delete(self.model) and soft_delete:
            self.statement = self.statement.where(self.model.deleted_at == None)
        count_statement = select(func.count()).select_from(self.statement.subquery())
        result = await self.session.exec(count_statement)
        return result.one() or 0

    async def pagination_async(
        self, pagination: PaginationRequest, soft_delete: bool = True
    ) -> PaginationResponse:
        if pagination.page <= 0 or pagination.limit <= 0:
            raise HTTPException(status_code=400, detail="Invalid pagination")

        if self.statement is None:
            self.statement = select(self.model)

        if self.is_has_soft_delete(self.model) and soft_delete:
            self.statement = self.statement.where(self.model.deleted_at == None)

        if pagination.filters:
            for f in pagination.filters:
                if f.field and hasattr(self.model, f.field):
                    column = getattr(self.model, f.field)
                    self.statement = self.statement.where(column == f.value)

        if pagination.search:
            search_conditions = []
            table = getattr(self.model, "__table__", None)
            if table is not None:
                for column in table.columns:
                    if isinstance(column.type, String):
                        search_conditions.append(column.ilike(f"%{pagination.search}%"))

            if search_conditions:
                self.statement = self.statement.where(or_(*search_conditions))

        count_statement = select(func.count()).select_from(self.statement.subquery())
        total = (await self.session.exec(count_statement)).one() or 0

        if pagination.sort_field and hasattr(self.model, pagination.sort_field):
            sort_column = getattr(self.model, pagination.sort_field)
            if pagination.is_desc:
                self.statement = self.statement.order_by(desc(sort_column))
            else:
                self.statement = self.statement.order_by(asc(sort_column))
        else:
            sort_col: Any = cast(Any, self.model)
            if self.is_has_updated_at(self.model):
                sort_col = cast(Any, self.model.updated_at)
            elif self.is_has_created_at(self.model):
                sort_col = cast(Any, self.model.created_at)

            self.statement = self.statement.order_by(
                desc(sort_col) if pagination.is_desc else asc(sort_col)
            )

        offset = (pagination.page - 1) * pagination.limit
        self.statement = self.statement.offset(offset).limit(pagination.limit)
        result = await self.session.exec(self.statement)
        data = result.all()
        if self.dto_class and data:
            data = [
                self.dto_class.model_validate(row, from_attributes=True) for row in data
            ]
        return PaginationResponse(
            page=pagination.page,
            limit=pagination.limit,
            total=total,
            total_items=total,
            data=list(data) or None,
        )

    async def cursor_pagination_async(
        self,
        cursor_request: CursorPaginationRequest,
        cursor_field: Optional[str] = None,
        soft_delete: bool = True,
    ) -> CursorPaginationResponse:
        if self.statement is None:
            self.statement = select(self.model)

        if self.is_has_soft_delete(self.model) and soft_delete:
            self.statement = self.statement.where(self.model.deleted_at == None)

        stmt = cast(Any, self.statement)
        limit = cursor_request.limit
        is_desc = cursor_request.is_desc

        cursor_time = None
        cursor_id = None
        if cursor_request.cursor:
            parts = cursor_request.cursor.split("_", 1)
            if len(parts) == 2:
                try:
                    cursor_time = parts[0]
                    cursor_id = int(parts[1])
                except Exception:
                    cursor_time = None
                    cursor_id = None
            else:
                try:
                    cursor_time = parts[0]
                except Exception:
                    cursor_time = None
                    cursor_id = None

        sort_field_name = cursor_field
        if sort_field_name is None:
            if self.is_has_updated_at(self.model):
                sort_field_name = "updated_at"
            else:
                sort_field_name = "created_at"

        sort_column = getattr(self.model, sort_field_name, None)

        if sort_column is not None:
            sort_column = cast(Any, sort_column)
            stmt = stmt.order_by(desc(sort_column) if is_desc else asc(sort_column))

        primary_key = getattr(self.model, "id", None)
        primary_key = cast(Any, primary_key)

        if cursor_id is not None and primary_key is not None:
            if is_desc:
                stmt = stmt.where(
                    or_(
                        cast(Any, sort_column) < cursor_time,
                        cast(Any, sort_column) == cursor_time,
                        cast(Any, primary_key) < cursor_id,
                    )
                )
            else:
                stmt = stmt.where(
                    or_(
                        cast(Any, sort_column) > cursor_time,
                        cast(Any, sort_column) == cursor_time,
                        cast(Any, primary_key) > cursor_id,
                    )
                )

        stmt = stmt.limit(limit)
        result = await self.session.exec(stmt)
        data = result.all()
        if self.dto_class and data:
            data = [
                self.dto_class.model_validate(row, from_attributes=True) for row in data
            ]

        next_cursor = None
        has_more = False
        if data:
            last = data[-1]
            last_sort = getattr(last, sort_field_name, None)
            last_id = getattr(last, "id", None)
            sort_val = last_sort if last_sort is not None else ""
            id_val = last_id if last_id is not None else 0
            next_cursor = f"{sort_val}_{id_val}"
            has_more = len(data) >= limit

        return CursorPaginationResponse(
            data=list(data) if data else None,
            next_cursor=next_cursor,
            has_more=has_more,
        )
