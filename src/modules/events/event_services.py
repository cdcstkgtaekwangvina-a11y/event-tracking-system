import asyncio
from datetime import datetime, timezone

from sqlalchemy import and_, or_
from sqlmodel import col

from database.models.app_db import SessionDep, SessionFactoryDep
from database.models.events import EVENT_STATUS, Events
from database.models.events_employees import EVENT_EMPLOYEE_STATUS, EventsEmployees
from src.shared.base import BaseCrud, BaseResponse
from src.shared.constants.cache_tags import CacheTags
from src.shared.helpers.time_extensions import get_vn_time
from src.shared.schemas.pagination_schemas import PaginationRequest, PaginationResponse
from src.shared.services.redis_services import RedisDep

from .event_schemas import (
    AdminEventQuery,
    CheckInEmployeeRequest,
    EmployeeIdsSchema,
    EmployeeInEvent,
    EventCreateRequest,
    EventsPagination,
    EventUpdateRequest,
    PublicEventQuery,
)


class EventServices:
    def __init__(
        self,
        session: SessionDep,
        factory: SessionFactoryDep,
        redis: RedisDep,
    ):
        self.session = session
        self.crud = BaseCrud[Events](session, Events)
        self.ee_crud = BaseCrud[EventsEmployees](session, EventsEmployees)
        self.factory = factory
        self.redis = redis

    async def create_event(self, event: EventCreateRequest) -> BaseResponse[Events]:
        new_event = await self.crud.create(event)
        return BaseResponse.created(new_event, message="Tạo sự kiện thành công")

    async def get_events_raw(self, pagination: PaginationRequest) -> PaginationResponse:
        return await self.crud.select(
            EventsPagination,
        ).pagination_async(pagination)

    async def get_public_events_raw(
        self, pagination: PublicEventQuery
    ) -> PaginationResponse:
        """Return only events that are in progress or have not started yet."""
        now = datetime.now(timezone.utc)

        if pagination.status == "ongoing":
            time_condition = and_(
                col(Events.start_at) <= now,
                or_(col(Events.end_at).is_(None), col(Events.end_at) >= now),
            )
        elif pagination.status == "upcoming":
            time_condition = col(Events.start_at) > now
        else:
            # An event is visible when it has not ended. Events without a start
            # time are excluded because their state cannot be determined.
            time_condition = and_(
                col(Events.start_at).is_not(None),
                or_(col(Events.end_at).is_(None), col(Events.end_at) >= now),
            )

        return (
            await self.crud.select(EventsPagination)
            .where(
                and_(col(Events.status) == EVENT_STATUS.PUBLISHED.value, time_condition)
            )
            .pagination_async(
                pagination,
                search_fields=[
                    EventsPagination.nameof(lambda x: x.name),
                    EventsPagination.nameof(lambda x: x.location),
                ],
            )
        )

    async def get_admin_events_raw(
        self, pagination: AdminEventQuery
    ) -> PaginationResponse:
        """Return the event history for administrators, optionally by status."""
        now = datetime.now(timezone.utc)
        time_condition = None

        if pagination.status == "ongoing":
            time_condition = and_(
                col(Events.start_at) <= now,
                or_(col(Events.end_at).is_(None), col(Events.end_at) >= now),
            )
        elif pagination.status == "upcoming":
            time_condition = col(Events.start_at) > now
        elif pagination.status == "ended":
            time_condition = col(Events.end_at) < now

        self.crud.select(EventsPagination)
        if time_condition is not None:
            self.crud.statement.where(time_condition)
        return await self.crud.pagination_async(
            pagination,
            search_fields=[
                EventsPagination.nameof(lambda x: x.name),
                EventsPagination.nameof(lambda x: x.location),
            ],
        )

    async def get_events(
        self, pagination: PaginationRequest
    ) -> BaseResponse[PaginationResponse]:
        result = await self.get_events_raw(pagination)
        return BaseResponse.ok(result, message="Lấy danh sách sự kiện thành công")

    async def get_event_by_id(self, event_id: int) -> BaseResponse[Events]:
        event = await self.crud.find_by_id(event_id)
        if not event:
            return BaseResponse.not_found(message="Không tìm thấy sự kiện")
        return BaseResponse.ok(event, message="Lấy chi tiết sự kiện thành công")

    async def get_employee_in_event(
        self, event_id: int, employee_id: int
    ) -> BaseResponse[EmployeeInEvent]:
        from database.models.employees import Employees

        employee = (
            await self.ee_crud.select(
                EmployeeInEvent,
                logic_column=[
                    Employees.name,
                    Employees.email,
                    Employees.position,
                    Employees.gender,
                    Employees.department,
                    Employees.starting_date,
                ],
            )
            .join(Employees)
            .where(
                and_(
                    col(EventsEmployees.event_id) == event_id,
                    col(EventsEmployees.employee_id) == employee_id,
                )
            )
            .find_one(dto_class=EmployeeInEvent)
        )

        if not employee:
            return BaseResponse.not_found(message="Không tìm thấy khách mời")

        return BaseResponse.ok(employee)

    async def update_event(
        self, event_id: int, event_data: EventUpdateRequest
    ) -> BaseResponse[Events]:
        db_obj = await self.crud.find_by_id(event_id)
        if db_obj is None:
            return BaseResponse.not_found(message="Không tìm thấy sự kiện")

        # Hỗ trợ cập nhật một phần (PATCH-style)
        update_dict = event_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_obj, key, value)

        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return BaseResponse.ok(db_obj, message="Cập nhật sự kiện thành công")

    async def delete_event(self, event_id: int) -> BaseResponse:
        deleted = await self.crud.delete(event_id)
        if not deleted:
            return BaseResponse.not_found(message="Không tìm thấy sự kiện")
        return BaseResponse.ok(message="Xóa sự kiện thành công")

    async def register_employee(
        self, event_id: int, schema: EmployeeIdsSchema
    ) -> BaseResponse[bool]:

        from database.models.employees import Employees

        async def exiting_employees() -> list[int] | None:
            async with self.factory() as session:
                crud = BaseCrud[Employees](session, Employees)
                emps = (
                    await crud.select(Employees.id)
                    .where(col(Employees.id).in_(schema.employee_ids))
                    .find_many()
                )

                if emps is None or len(emps) == 0:
                    return None
                return list(emps)

        async def exiting_employees_already_registered() -> list[int] | None:
            async with self.factory() as session:
                crud = BaseCrud[EventsEmployees](session, EventsEmployees)
                emps = (
                    await crud.select(EventsEmployees.employee_id)
                    .where(
                        and_(
                            col(EventsEmployees.event_id) == event_id,
                            col(EventsEmployees.employee_id).in_(schema.employee_ids),
                        )
                    )
                    .find_many()
                )

                if emps is None or len(emps) == 0:
                    return None
                return list(emps)

        exiting_emps, exiting_emp_already_regis = await asyncio.gather(
            exiting_employees(), exiting_employees_already_registered()
        )

        exiting_event = (
            await self.crud.select(Events.id).where(Events.id == event_id).any_async()
        )

        if not exiting_event:
            return BaseResponse.not_found(message="Không tìm thấy sự kiện")

        if exiting_emps is None:
            return BaseResponse.not_found(message="Không tìm thấy khách mời")

        new_emps: set[int] = set()
        if exiting_emp_already_regis is not None:
            new_emps = set(schema.employee_ids) - set(exiting_emp_already_regis)
        else:
            new_emps = set(schema.employee_ids)

        register_emps = []
        for emp in new_emps:
            register_emps.append(
                EventsEmployees(
                    event_id=event_id, employee_id=emp, join_at=get_vn_time()
                )
            )

        if len(register_emps) > 0:
            self.session.add_all(register_emps)
            await self.session.commit()
            await self.redis.invalidate_tags_async(
                [CacheTags.EMPLOYEE, CacheTags.EVENT]
            )
        return BaseResponse.created(True, message="Đăng ký thành công")

    async def remove_employee_froms_event(
        self, event_id: int, schema: EmployeeIdsSchema
    ) -> BaseResponse[None]:
        exiting_event = (
            await self.crud.select(Events.id).where(Events.id == event_id).any_async()
        )

        if not exiting_event:
            return BaseResponse.not_found(message="Không tìm thấy sự kiện")

        remove_emps = await self.ee_crud.delete(
            condition=lambda x: (
                (x.employee_id.in_(schema.employee_ids)) & (x.event_id == event_id)
            ),
            soft_delete=False,
        )

        if remove_emps:
            await self.redis.invalidate_tags_async(
                [CacheTags.EMPLOYEE, CacheTags.EVENT]
            )
            return BaseResponse.no_content()

        return BaseResponse.fail(message="Xóa thất bại")

    async def check_in_employee(
        self, schema: CheckInEmployeeRequest
    ) -> BaseResponse[bool]:
        from sqlmodel import update

        check_in_employee = await self.session.exec(
            update(EventsEmployees)
            .where(
                and_(
                    col(EventsEmployees.employee_id) == schema.employee_id,
                    col(EventsEmployees.event_id) == schema.event_id,
                )
            )
            .values(
                {
                    "check_in_at": get_vn_time(),
                    "status": EVENT_EMPLOYEE_STATUS.CHECK_IN.value,
                }
            )
        )
        await self.session.commit()

        if check_in_employee.rowcount > 0:
            await self.redis.invalidate_tags_async([CacheTags.EMPLOYEE])
            return BaseResponse.ok(True)

        return BaseResponse.fail(
            message="Check in thất bại, khách mời hoặc sự kiện không đúng"
        )
