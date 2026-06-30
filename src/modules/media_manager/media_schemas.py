from fastapi import UploadFile, Form
from src.shared.base.base_schema import BaseSchema
from typing import Optional, Any
from pydantic import Field, model_validator
from datetime import datetime


class MediaSchema(BaseSchema):
    id: int
    name: str
    url: str | None
    prefix: list[dict[str, Any]] | None = None
    media_metadata: dict[str, Any] | None
    parent_id: int | None
    is_folder: bool
    created_at: datetime
    updated_at: datetime | None


class CreateMediaSchema(BaseSchema):
    name: str = Field(..., max_length=800, description="Tên của file hoặc thư mục")
    folder_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="ID của thư mục cha (parent_id), để trống nếu nằm ở thư mục gốc",
    )
    is_folder: bool = Field(
        default=True, description="True nếu là thư mục, False nếu là file"
    )
    file: Optional[UploadFile] = Field(
        default=None,
        description="Tập tin đính kèm (Bắt buộc phải có nếu is_folder = False)",
    )

    # =================================================================
    # 🔥 BỘ LỌC TỰ ĐỘNG: Kiểm tra tính hợp lệ giữa Loại dữ liệu và File
    # =================================================================
    @model_validator(mode="after")
    def validate_file_and_type(self) -> "CreateMediaSchema":
        # Nếu thiết lập là File (is_folder = False) mà người dùng không đính kèm file
        if not self.is_folder and self.file is None:
            raise ValueError("File không được để trống khi tạo tập tin.")

        # Nếu thiết lập là Thư mục (is_folder = True) mà lại truyền thừa file lên
        if self.is_folder and self.file is not None:
            self.file = None  # Tự động loại bỏ file thừa để sạch DB

        return self

    # =================================================================
    # 💡 CẤU HÌNH LIÊN KẾT FORM-DATA (Dành cho FastAPI Upload File)
    # =================================================================
    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        folder_id: Optional[int] = Form(None),
        is_folder: bool = Form(False),
        file: Optional[UploadFile] = Form(None),
    ) -> "CreateMediaSchema":
        """
        Hàm helper biến Schema này thành dạng Form-Data.
        Vì FastAPI không thể parse trực tiếp JSON chứa đối tượng UploadFile.
        """
        return cls(name=name, folder_id=folder_id, is_folder=is_folder, file=file)


class UpdateMedia(BaseSchema):
    name: Optional[str] = Field(max_length=800, default=None)
    folder_id: Optional[int] = Field(ge=-1, default=None)

    @model_validator(mode="after")
    def validate_folder_and_name(self) -> "UpdateMedia":
        if self.name is None and self.folder_id is None:
            raise ValueError("Không có dữ liệu để update")
        return self


class BulkDeleteSchema(BaseSchema):
    ids: list[int] = Field(..., min_length=1, description="Danh sách ID cần xóa")
    is_soft_delete: bool = Field(
        default=True, description="True = xóa mềm, False = xóa vĩnh viễn"
    )


class MediaMetaData(BaseSchema):
    type: Optional[str] = None
    sizes: int = Field(gt=0)
    format: Optional[str] = Field(max_length=100)


class PrefixNode(BaseSchema):
    id: int | None
    name: str | None
