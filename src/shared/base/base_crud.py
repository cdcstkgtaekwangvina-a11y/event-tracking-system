from src.shared.helpers.time_extensions import get_now_vn
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel, select
from sqlmodel.sql.expression import SelectOfScalar
from typing import TypeVar, Generic, Type, Optional, TypeGuard, Any, Sequence, cast
from sqlalchemy import func, exists, or_, desc, asc, String
from fastapi import HTTPException
from src.shared.schemas.pagination_schemas import PaginationRequest, PaginationResponse
from database.models.base_model import (
    PrimaryModel,
    CreatedAtModel,
    UpdatedAtModel,
    DeletedAtModel,
)

T = TypeVar("T", bound=SQLModel)


class BaseCrud(Generic[T]):
    model: Type[T]
    id_type: Any
    session: AsyncSession

    def __init__(self, session: AsyncSession):
        self.session = session

    def is_has_soft_delete(self, model: Type[T]) -> TypeGuard[Type[DeletedAtModel]]:
        return isinstance(model, type) and issubclass(model, DeletedAtModel)

    def is_has_created_at(self, model: Type[T]) -> TypeGuard[Type[CreatedAtModel]]:
        return isinstance(model, type) and issubclass(model, CreatedAtModel)

    def is_has_updated_at(self, model: Type[T]) -> TypeGuard[Type[UpdatedAtModel]]:
        return isinstance(model, type) and issubclass(model, UpdatedAtModel)

    def is_has_primary_key(self, model: Type[T]) -> TypeGuard[Type[PrimaryModel]]:
        return isinstance(model, type) and issubclass(model, PrimaryModel)

    async def create(self, data) -> Optional[T]:
        db_obj = self.model(**data.model_dump())
        self.session.add(db_obj)
        await self.session.commit()
        return db_obj

    async def find_one(
        self, statement: Optional[SelectOfScalar[T]] = None
    ) -> Optional[T]:
        if statement is None:
            statement = select(self.model)
        if self.is_has_soft_delete(self.model):
            statement = statement.where(self.model.deleted_at == None)

        result = await self.session.exec(statement)
        return result.first()

    async def find_by_id(self, id: Any) -> Optional[T]:
        statement = select(self.model)
        if self.is_has_soft_delete(self.model):
            statement = statement.where(self.model.deleted_at == None)

        if self.is_has_primary_key(self.model):
            statement = statement.where(self.model.id == id)
        else:
            raise HTTPException(
                status_code=500, detail="Model does not have a primary key"
            )

        result = await self.session.exec(statement)
        return result.first()

    async def find_many(
        self, statement: Optional[SelectOfScalar[T]] = None
    ) -> Sequence[T]:
        if statement is None:
            statement = select(self.model)
        if self.is_has_soft_delete(self.model):
            statement = statement.where(self.model.deleted_at == None)
        result = await self.session.exec(statement)
        return result.all()

    async def update(self, id: Any, data: Any) -> Optional[T]:
        db_obj = await self.find_by_id(id)
        if db_obj is None:
            return None
        for key, value in data.model_dump().items():
            setattr(db_obj, key, value)
        self.session.add(db_obj)
        await self.session.commit()
        return db_obj

    async def delete(self, id: Any, is_soft_delete: bool = True) -> bool:
        db_obj = await self.find_by_id(id)
        if db_obj is None:
            return False
        if is_soft_delete:
            db_obj.deleted_at = get_now_vn()
            self.session.add(db_obj)
            await self.session.commit()
            return True
        else:
            await self.session.delete(db_obj)
            await self.session.commit()
            return True

    async def any(self, statement: Optional[SelectOfScalar[T]] = None) -> bool:
        if statement is None:
            statement = select(self.model)
        if self.is_has_soft_delete(self.model):
            statement = statement.where(self.model.deleted_at == None)
        stmt = select(exists(statement))
        result = await self.session.exec(stmt)
        return bool(result.first())

    async def count(self, statement: Optional[SelectOfScalar[T]] = None) -> int:
        if statement is None:
            statement = select(self.model)
        if self.is_has_soft_delete(self.model):
            statement = statement.where(self.model.deleted_at == None)
        count_statement = select(func.count()).select_from(statement.subquery())
        result = await self.session.exec(count_statement)
        return result.one() or 0

    async def pagination_async(
        self,
        pagination: PaginationRequest,
        statement: Optional[SelectOfScalar[T]] = None,
    ) -> PaginationResponse:
        if pagination.page <= 0 or pagination.limit <= 0:
            raise HTTPException(status_code=400, detail="Invalid pagination")

        if statement is None:
            statement = select(self.model)

        if self.is_has_soft_delete(self.model):
            statement = statement.where(self.model.deleted_at == None)

        if pagination.filters:
            for f in pagination.filters:
                if f.field and hasattr(self.model, f.field):
                    column = getattr(self.model, f.field)
                    statement = statement.where(column == f.value)

        if pagination.search:
            search_conditions = []
            table = getattr(self.model, "__table__", None)
            if table is not None:
                for column in table.columns:
                    if isinstance(column.type, String):
                        search_conditions.append(column.ilike(f"%{pagination.search}%"))

            if search_conditions:
                statement = statement.where(or_(*search_conditions))

        count_statement = select(func.count()).select_from(statement.subquery())
        total = (await self.session.exec(count_statement)).one() or 0

        if pagination.sort_field and hasattr(self.model, pagination.sort_field):
            sort_column = getattr(self.model, pagination.sort_field)
            if pagination.is_desc:
                statement = statement.order_by(desc(sort_column))
            else:
                statement = statement.order_by(asc(sort_column))
        else:
            if self.is_has_created_at(self.model):
                created_at_col = cast(Any, self.model.created_at)

                statement = statement.order_by(
                    desc(created_at_col) if pagination.is_desc else asc(created_at_col)
                )

        offset = (pagination.page - 1) * pagination.limit
        statement = statement.offset(offset).limit(pagination.limit)
        result = await self.session.exec(statement)
        data = result.all()

        return PaginationResponse(
            page=pagination.page,
            limit=pagination.limit,
            total=total,
            total_items=total,
            data=list(data),
        )
