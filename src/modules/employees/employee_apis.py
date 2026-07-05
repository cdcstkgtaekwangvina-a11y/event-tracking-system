from src.shared.base import BaseRouter
from src.shared.helpers.cbv import clean_cbv
from .employee_services import EmployeeServices
from fastapi import Depends

TAG_NAME = "employees"
router = BaseRouter(controller=TAG_NAME, tags=[TAG_NAME])


@clean_cbv(router)
class EmployeeController:
    def __init__(self, service: EmployeeServices = Depends()):
        self.service = service
