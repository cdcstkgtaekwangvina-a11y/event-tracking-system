from io import BytesIO
from typing import Any, Literal

from polars import DataFrame, DataType, read_csv, read_excel, read_json, read_ndjson


class FileHandelHelper:
    def __read_excel(
        self,
        buffer: BytesIO,
        analytics_file: bool = True,
        header_row: int | None = None,
        **kwargs,
    ) -> DataFrame | None:
        # Trường hợp 1: Có chỉ định dòng header rõ ràng
        if header_row is not None:
            return read_excel(buffer, read_options={"header_row": header_row}, **kwargs)

        # Trường hợp 2: Bỏ qua phân tích, đọc mặc định theo Polars
        if not analytics_file:
            return read_excel(buffer, **kwargs)

        # Trường hợp 3: Phân tích file (analytics_file == True)
        df_sample = read_excel(buffer, has_header=False, **kwargs).head(50)

        if df_sample.is_empty():
            return None

        rows = df_sample.rows()
        global_max_cols = 0
        row_analysis = []

        # BƯỚC 1: Quét tìm số cột tối đa có dữ liệu
        for i, row in enumerate(rows):
            valid_cells = [c for c in row if c is not None and str(c).strip() != ""]
            col_count = len(valid_cells)
            text_count = sum(1 for c in valid_cells if isinstance(c, str))

            if col_count > global_max_cols:
                global_max_cols = col_count

            row_analysis.append(
                {
                    "index": i,
                    "col_count": col_count,
                    "is_mostly_text": (text_count / col_count >= 0.5)
                    if col_count > 0
                    else False,
                }
            )

        # BƯỚC 2: Quyết định dòng Header (Dòng đầu tiệm cận max cột & chủ yếu là text)
        has_header = False
        guessed_header_index = 0
        for item in row_analysis:
            if (
                item["col_count"] >= max(1, global_max_cols - 1)
                and item["is_mostly_text"]
            ):
                has_header = True
                guessed_header_index = item["index"]
                break

        # BƯỚC 3: Đọc file chính thức dựa vào kết quả đoán
        buffer.seek(0)

        if has_header:
            df = read_excel(
                buffer, read_options={"header_row": guessed_header_index}, **kwargs
            )
        else:
            df = read_excel(buffer, has_header=False, **kwargs)

        return df

    def __read_csv(
        self,
        buffer: BytesIO,
        analytics_file: bool = True,
        header_row: int | None = None,
        **kwargs,
    ) -> DataFrame | None:
        # Trường hợp 1: Có chỉ định dòng header rõ ràng
        if header_row is not None:
            return read_csv(buffer, has_header=True, skip_rows=header_row, **kwargs)

        # Trường hợp 2: Bỏ qua phân tích, đọc mặc định theo Polars
        if not analytics_file:
            return read_csv(buffer, **kwargs)

        # Trường hợp 3: Phân tích file (analytics_file == True)
        try:
            df_sample = read_csv(buffer, has_header=False, n_rows=50, **kwargs)
        except Exception:
            buffer.seek(0)
            df_sample = read_csv(
                buffer, has_header=False, n_rows=50, encoding="utf-8-lossy", **kwargs
            )

        if df_sample.is_empty():
            return None

        rows = df_sample.rows()
        global_max_cols = 0
        row_analysis = []

        # BƯỚC 1: Quét tìm số cột tối đa có dữ liệu
        for i, row in enumerate(rows):
            valid_cells = [c for c in row if c is not None and str(c).strip() != ""]
            col_count = len(valid_cells)
            text_count = sum(1 for c in valid_cells if isinstance(c, str))

            if col_count > global_max_cols:
                global_max_cols = col_count

            row_analysis.append(
                {
                    "index": i,
                    "col_count": col_count,
                    "is_mostly_text": (text_count / col_count >= 0.5)
                    if col_count > 0
                    else False,
                }
            )

        # BƯỚC 2: Quyết định dòng Header
        has_header = False
        guessed_header_index = 0
        for item in row_analysis:
            if (
                item["col_count"] >= max(1, global_max_cols - 1)
                and item["is_mostly_text"]
            ):
                has_header = True
                guessed_header_index = item["index"]
                break

        # BƯỚC 3: Đọc file chính thức dựa vào kết quả đoán
        buffer.seek(0)

        if has_header:
            df = read_csv(
                buffer, has_header=True, skip_rows=guessed_header_index, **kwargs
            )
        else:
            df = read_csv(buffer, has_header=False, **kwargs)

        return df

    def read_sheet_file(
        self,
        file_bytes: bytes,
        type: Literal["excel", "csv"],
        analytics_file: bool = True,
        header_row: int | None = None,
        **kwargs,
    ) -> DataFrame | None:
        buffer = BytesIO(file_bytes)

        match type:
            case "excel":
                return self.__read_excel(buffer, analytics_file, header_row, **kwargs)

            case "csv":
                return self.__read_csv(buffer, analytics_file, header_row, **kwargs)

            case _:
                raise ValueError("Invalid file type")

    def read_json(
        self,
        file: bytes,
        **kwargs,
    ) -> DataFrame | None:
        """
        Đọc file JSON từ bytes.
        JSON đã tự định nghĩa Header thông qua Key, nên không cần đoán cấu trúc.
        """
        buffer = BytesIO(file)
        try:
            df = read_json(buffer, **kwargs)
            return df if not df.is_empty() else None

        except Exception as e_json:
            try:
                buffer.seek(0)
                df = read_ndjson(buffer, **kwargs)
                return df if not df.is_empty() else None
            except Exception:
                raise ValueError(
                    f"Định dạng JSON không hợp lệ hoặc không được hỗ trợ. Lỗi: {str(e_json)}"
                )

    def _ensure_dataframe(self, data: DataType) -> DataFrame:
        """Tự động chuyển đổi dict/list thành Polars DataFrame nếu chưa phải"""
        if isinstance(data, DataFrame):
            return data
        if isinstance(data, (list, dict)):
            return DataFrame(data)
        raise TypeError(
            f"Dữ liệu không hợp lệ. Kỳ vọng DataFrame, list hoặc dict, nhưng nhận được {type(data).__name__}"
        )

    def export_csv_bytes(
        self,
        data: DataType,
        config: dict[str, Any] | None = None,
    ) -> bytes:
        df = self._ensure_dataframe(data)
        if df.is_empty():
            raise ValueError("Dữ liệu đang trống, không có gì để xuất.")

        config = config or {}
        buffer = BytesIO()
        df.write_csv(buffer, **config)
        return buffer.getvalue()

    def export_excel_bytes(
        self, data: DataType, config: dict[str, Any] | None = None
    ) -> bytes:
        df = self._ensure_dataframe(data)
        if df.is_empty():
            raise ValueError("Dữ liệu đang trống, không có gì để xuất.")

        config = config or {}
        buffer = BytesIO()
        df.write_excel(buffer, **config)
        return buffer.getvalue()

    def export_json_bytes(
        self, data: DataType, config: dict[str, Any] | None = None
    ) -> bytes:
        df = self._ensure_dataframe(data)
        if df.is_empty():
            raise ValueError("Dữ liệu đang trống, không có gì để xuất.")

        config = config or {}
        config.setdefault("row_oriented", True)
        buffer = BytesIO()
        df.write_json(buffer, **config)
        return buffer.getvalue()

    def export_file(
        self,
        data: DataType,
        type: Literal["excel", "csv", "json"],
        config: dict[str, Any] | None = None,
    ) -> bytes:
        """Hàm API công khai để xuất file (Truyền thẳng data kiểu DataType vào)"""
        match type:
            case "excel":
                return self.export_excel_bytes(data, config)
            case "csv":
                return self.export_csv_bytes(data, config)
            case "json":
                return self.export_json_bytes(data, config)
            case _:
                raise ValueError(f"Invalid export type: {type}")
