from fastapi import APIRouter, Depends, Request
from database.models.app_db import SessionDep
from .employee_schemas import EmployeeCreateRequest, EmployeeUpdateRequest
from database.models.employees import Employees
from .employee_services import EmployeeServices
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional
from src.shared.base import BaseResponse

TAG_NAME = "employees"
router = APIRouter(tags=[TAG_NAME])
controller = f"/{TAG_NAME}"
api = f"/api/{TAG_NAME}"


def get_employee_service(session: SessionDep) -> EmployeeServices:
    return EmployeeServices(session)


@router.post(f"{api}", response_class=JSONResponse)
async def create_employee(
    employee: EmployeeCreateRequest, services: EmployeeServices = Depends(get_employee_service)
) -> BaseResponse:
    return await services.create_employee(employee)


@router.get(f"{api}", response_class=JSONResponse)
async def get_employees(
    page: int = 1,
    limit: int = 10,
    sort_field: Optional[str] = None,
    is_desc: bool = False,
    search: Optional[str] = None,
    services: EmployeeServices = Depends(get_employee_service),
):
    from src.shared.schemas.pagination_schemas import PaginationRequest
    pagination = PaginationRequest(
        page=page,
        limit=limit,
        sort_field=sort_field,
        is_desc=is_desc,
        search=search,
    )
    return await services.get_employees(pagination)


@router.get(f"{api}/{{employee_id}}", response_class=JSONResponse)
async def get_employee_by_id(
    employee_id: int, services: EmployeeServices = Depends(get_employee_service)
) -> BaseResponse:
    return await services.get_employee_by_id(employee_id)


@router.put(f"{api}/{{employee_id}}", response_class=JSONResponse)
async def update_employee(
    employee_id: int,
    employee: EmployeeUpdateRequest,
    services: EmployeeServices = Depends(get_employee_service),
) -> BaseResponse:
    return await services.update_employee(employee_id, employee)


@router.delete(f"{api}/{{employee_id}}", response_class=JSONResponse)
async def delete_employee(
    employee_id: int, services: EmployeeServices = Depends(get_employee_service)
) -> BaseResponse:
    return await services.delete_employee(employee_id)
