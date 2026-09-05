from collections.abc import Iterable
from typing import Annotated

import puremagic
from fastapi import Depends, File, HTTPException, UploadFile, status
from puremagic.main import PureError

from src.shared.constants.file_type import FileMimeType


async def validate_file_type(
    file: UploadFile,
    allowed_types: Iterable[FileMimeType | str] | None = None,
    allowed_groups: Iterable[Iterable[FileMimeType | str]] | None = None,
) -> UploadFile:
    """
    Validate file content safety and type using `puremagic` (magic numbers / file headers).
    Can be used as a FastAPI Dependency or standalone helper function.

    - `allowed_types`: A collection of allowed MIME types (e.g., [FileMimeType.JPEG, FileMimeType.PNG] or FileGroup.IMAGES).
    - `allowed_groups`: A collection of groups to allow.
    """
    # 1. Read the beginning of the file to inspect magic numbers (e.g., first 2048 bytes)
    # UploadFile.read() is async. We read a chunk, then seek back to 0 so subsequent handlers can still read it.
    header_chunk = await file.read(2048)
    await file.seek(0)

    if not header_chunk:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tập tin tải lên trống (file is empty).",
        )

    try:
        # puremagic.from_string returns the detected MIME type as a string (e.g., "application/pdf")
        detected_mime: str = puremagic.from_string(header_chunk, mime=True).lower()
    except PureError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể phân tích định dạng tập tin: {str(e)}",
        )

    if not detected_mime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xác định được định dạng thực tế của tập tin.",
        )

    # Flatten allowed types/groups into a unified set of valid MIME strings
    valid_mime_set: set[str] = set()

    if allowed_types:
        for t in allowed_types:
            valid_mime_set.add(str(t).lower())

    if allowed_groups:
        for group in allowed_groups:
            for t in group:
                valid_mime_set.add(str(t).lower())

    # If no restrictions are specified, we just return the file after successful magic check
    if not valid_mime_set:
        return file

    # Check if detected MIME type matches any allowed type
    is_valid = detected_mime in valid_mime_set

    # Also handle some edge cases where mime mappings might slightly differ (e.g., image/jpg vs image/jpeg)
    if not is_valid:
        if detected_mime == "image/jpg" and FileMimeType.JPEG in valid_mime_set:
            is_valid = True

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng tập tin không được phép ({detected_mime}). Các định dạng hỗ trợ: {', '.join(valid_mime_set)}",
        )

    return file


def create_file_validator(
    allowed_types: Iterable[FileMimeType | str] | None = None,
    allowed_groups: Iterable[Iterable[FileMimeType | str]] | None = None,
):
    """
    Factory to create a FastAPI Dependency with pre-configured allowed types/groups.

    Usage in router:
        from src.shared.validators.file_validators import create_file_validator
        from src.shared.constants.file_type import FileGroup

        @router.post("/upload")
        async def upload(file: UploadFile = Depends(create_file_validator(allowed_types=FileGroup.IMAGES))):
            ...
    """

    async def dependency(file: UploadFile = File(...)) -> UploadFile:
        return await validate_file_type(
            file, allowed_types=allowed_types, allowed_groups=allowed_groups
        )

    return dependency


from src.shared.constants.file_type import FileGroup

ImageFile = Annotated[
    UploadFile, Depends(create_file_validator(allowed_groups=[FileGroup.IMAGES]))
]
DocumentFile = Annotated[
    UploadFile, Depends(create_file_validator(allowed_groups=[FileGroup.DOCUMENTS]))
]
AllFileType = Annotated[
    UploadFile, Depends(create_file_validator(allowed_groups=[FileGroup.ALL_TYPES]))
]
