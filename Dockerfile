# ==============================================================================
# Stage 1: Builder — cài đặt dependencies bằng uv
# ==============================================================================
#FROM python:3.14-slim AS runtime
FROM python:3.14-freethreaded-slim AS builder

# Cài uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy file requirements trước để tận dụng Docker layer cache
COPY requirements.txt .

# Cài dependencies vào virtual env bằng uv
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python -r requirements.txt && \
    uv pip install --python /app/.venv/bin/python granian uvloop


# ==============================================================================
# Stage 2: Runtime — image chạy production
# ==============================================================================
#FROM python:3.14-slim AS runtime
FROM python:3.14-freethreaded-slim AS runtime

# Metadata
LABEL maintainer="event-tracking-system"
LABEL description="FastAPI Event Tracking System with Granian + uvloop"

# Biến môi trường
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    #ẩn nếu bản python không gil bị lỗi
    PYTHON_GIL=0 \
    PATH="/app/.venv/bin:$PATH" \
    env=production

WORKDIR /app

# Tạo user non-root để chạy app
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Copy virtual env từ builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY alembic.ini .
COPY database/ ./database/
COPY public/ ./public/
COPY src/ ./src/

# Tạo thư mục uploads nếu cần
RUN mkdir -p /app/uploads && chown -R appuser:appuser /app

# Chuyển sang user non-root
USER appuser

# Expose port (mặc định 4000, có thể override bằng env)
EXPOSE 4000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-4000}/docs')" || exit 1

# Khởi chạy Granian với uvloop
CMD ["granian", \
    "--interface", "asgi", \
    "--loop", "uvloop", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--workers", "4", \
    "--backpressure", "128", \
    "src.main:app"]
