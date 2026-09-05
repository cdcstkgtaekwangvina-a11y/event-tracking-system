from enum import StrEnum


class FileMimeType(StrEnum):
    # 1. Văn bản & Tài liệu căn bản
    TXT = "text/plain"
    MARKDOWN = "text/markdown"
    HTML = "text/html"
    JSON = "application/json"
    PDF = "application/pdf"

    # 2. Microsoft Office & Excel/CSV
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    DOC = "application/msword"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    XLS = "application/vnd.ms-excel"
    CSV = "text/csv"

    # 3. Hình ảnh (Images)
    JPEG = "image/jpeg"
    PNG = "image/png"
    GIF = "image/gif"
    WEBP = "image/webp"
    SVG = "image/svg+xml"

    # 4. Video
    MP4 = "video/mp4"
    WEBM = "video/webm"
    MOV = "video/quicktime"
    AVI = "video/x-msvideo"

    # 5. Âm thanh (Audio)
    MP3 = "audio/mpeg"
    WAV = "audio/wav"
    AAC = "audio/aac"
    OGG = "audio/ogg"

    # 6. File nén
    ZIP = "application/zip"
    RAR = "application/vnd.rar"


# --- CÁCH GOM NHÓM ĐỂ TIỆN SỬ DỤNG ---
class FileGroup:
    IMAGES = [
        FileMimeType.JPEG,
        FileMimeType.PNG,
        FileMimeType.WEBP,
        FileMimeType.GIF,
        FileMimeType.SVG,
    ]

    DOCUMENTS = [
        FileMimeType.PDF,
        FileMimeType.DOCX,
        FileMimeType.DOC,
        FileMimeType.TXT,
        FileMimeType.MARKDOWN,
    ]

    DATA_SHEETS = [
        FileMimeType.XLSX,
        FileMimeType.XLS,
        FileMimeType.CSV,
        FileMimeType.JSON,
    ]

    AUDIO = [FileMimeType.MP3, FileMimeType.WAV, FileMimeType.OGG, FileMimeType.AAC]
    VIDEO = [FileMimeType.MP4, FileMimeType.WEBM, FileMimeType.MOV, FileMimeType.AVI]
    MEDIA = [*AUDIO, *VIDEO]

    ALL_TYPES = [FileMimeType.HTML, *IMAGES, *DOCUMENTS, *DATA_SHEETS, *MEDIA]
