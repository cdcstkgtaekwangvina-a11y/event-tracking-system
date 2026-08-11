from database.models.app_db import SessionDep
from database.models.events import Events
from database.models.events_employees import EventsEmployees
from src.shared.base import BaseCrud, BaseResponse
from src.shared.schemas.pagination_schemas import PaginationRequest, PaginationResponse
from .event_schemas import (
    EventCreateRequest,
    EventUpdateRequest,
    EventsSchema,
    AdminEventQuery,
    PublicEventQuery,
)
from sqlalchemy import and_, func, or_
from typing import Any, cast
from datetime import datetime, timezone


class EventServices:
    def __init__(self, session: SessionDep):
        self.session = session
        self.crud = BaseCrud[Events](session, Events)

    async def create_event(self, event: EventCreateRequest) -> BaseResponse[Events]:
        new_event = await self.crud.create(event)
        return BaseResponse.created(new_event, message="Tạo sự kiện thành công")

    async def get_events_raw(self, pagination: PaginationRequest) -> PaginationResponse:
        self.crud.select(
            EventsSchema,
            logic_column=[
                func.count(cast(Any, EventsEmployees.employee_id)).label(
                    EventsSchema.nameof(lambda e: e.employee_count)
                ),
            ],
        ).join(
            target=EventsEmployees,
            onclause=EventsEmployees.event_id == Events.id,
            isouter=True,
        ).group_by(Events.id)
        return await self.crud.pagination_async(pagination)

    async def get_public_events_raw(
        self, pagination: PublicEventQuery
    ) -> PaginationResponse:
        """Return only events that are in progress or have not started yet."""
        now = datetime.now(timezone.utc)

        if pagination.status == "ongoing":
            time_condition = and_(
                Events.start_at <= now,
                or_(Events.end_at.is_(None), Events.end_at >= now),
            )
        elif pagination.status == "upcoming":
            time_condition = Events.start_at > now
        else:
            # An event is visible when it has not ended. Events without a start
            # time are excluded because their state cannot be determined.
            time_condition = and_(
                Events.start_at.is_not(None),
                or_(Events.end_at.is_(None), Events.end_at >= now),
            )

        self.crud.select(
            EventsSchema,
            logic_column=[
                func.count(cast(Any, EventsEmployees.employee_id)).label(
                    EventsSchema.nameof(lambda e: e.employee_count)
                ),
            ],
        ).join(
            target=EventsEmployees,
            onclause=EventsEmployees.event_id == Events.id,
            isouter=True,
        ).where(time_condition).group_by(Events.id)

        return await self.crud.pagination_async(
            pagination,
            search_fields=["name", "location", "description"],
        )

    async def get_admin_events_raw(
        self, pagination: AdminEventQuery
    ) -> PaginationResponse:
        """Return the event history for administrators, optionally by status."""
        now = datetime.now(timezone.utc)
        time_condition = None

        if pagination.status == "ongoing":
            time_condition = and_(
                Events.start_at <= now,
                or_(Events.end_at.is_(None), Events.end_at >= now),
            )
        elif pagination.status == "upcoming":
            time_condition = Events.start_at > now
        elif pagination.status == "ended":
            time_condition = Events.end_at < now

        query = self.crud.select(
            EventsSchema,
            logic_column=[
                func.count(cast(Any, EventsEmployees.employee_id)).label(
                    EventsSchema.nameof(lambda e: e.employee_count)
                ),
            ],
        ).join(
            target=EventsEmployees,
            onclause=EventsEmployees.event_id == Events.id,
            isouter=True,
        )
        if time_condition is not None:
            query.where(time_condition)
        query.group_by(Events.id)

        return await self.crud.pagination_async(
            pagination,
            search_fields=["name", "location", "description"],
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

    async def register_employee(self, event_id: int, employee_id: int) -> BaseResponse:
        from database.models.events_employees import EventsEmployees
        from database.models.employees import Employees
        from sqlmodel import select
        from datetime import datetime

        # Check if employee exists
        stmt_emp = select(Employees).where(Employees.id == employee_id)
        emp = (await self.session.exec(stmt_emp)).first()
        if not emp:
            return BaseResponse.fail(
                message=f"Không tìm thấy nhân viên với ID: {employee_id}"
            )

        # Check if event exists
        stmt_evt = select(Events).where(Events.id == event_id)
        evt = (await self.session.exec(stmt_evt)).first()
        if not evt:
            return BaseResponse.fail(message="Không tìm thấy sự kiện")

        # Check if already registered
        stmt_link = select(EventsEmployees).where(
            EventsEmployees.event_id == event_id,
            EventsEmployees.employee_id == employee_id,
        )
        link = (await self.session.exec(stmt_link)).first()
        if link:
            return BaseResponse.fail(
                message=f"Nhân viên {emp.name} đã đăng ký sự kiện này rồi"
            )

        # Create link
        new_link = EventsEmployees(
            event_id=event_id,
            employee_id=employee_id,
            status="PENDING",
            join_at=datetime.now(),
        )
        self.session.add(new_link)
        await self.session.commit()
        return BaseResponse.ok(message=f"Đăng ký thành công cho {emp.name}!")
