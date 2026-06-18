# Event Tracking System

Hệ thống quản lý và theo dõi sự kiện (events) cùng nhân viên (employees) tham gia, xây dựng theo kiến trúc **module hóa** trên nền **FastAPI**. Giao diện render phía server bằng **Jinja2** kết hợp **HTMX** + **Alpine.js** để tạo trải nghiệm động mà không cần một SPA framework riêng.

## Công nghệ sử dụng

### Backend

| Công nghệ | Vai trò trong dự án |
|-----------|---------------------|
| **FastAPI** | Web framework chính, định nghĩa API + view routes, dependency injection, validation. |
| **Granian** | ASGI server (thay cho uvicorn) để chạy ứng dụng, hỗ trợ hot-reload ở môi trường `dev`. |
| **SQLModel** | ORM kết hợp giữa SQLAlchemy + Pydantic, dùng để định nghĩa model và truy vấn database. |
| **SQLAlchemy / asyncpg** | Engine async giao tiếp với PostgreSQL. |
| **Alembic** | Quản lý migration (version hóa schema database). |
| **Pydantic v2** | Định nghĩa schema request/response, validate dữ liệu vào/ra. |
| **Redis** | Cache dữ liệu và quản lý cache-tag để invalidate khi dữ liệu thay đổi. |
| **PyJWT / pwdlib (argon2)** | Xác thực bằng JWT và băm mật khẩu an toàn. |
| **Scalar** | Giao diện tài liệu API (chỉ bật ở môi trường `dev`). |

### Frontend (server-rendered)

| Công nghệ | Vai trò trong dự án |
|-----------|---------------------|
| **Jinja2** | Template engine render HTML phía server (các file `.j2`). |
| **HTMX** | Gửi request AJAX và cập nhật từng phần HTML mà không reload trang. |
| **Alpine.js** | Thêm tương tác/reactivity nhẹ trực tiếp trong markup. |
| **TipTap** | Rich text editor cho nội dung. |

### Database

- **PostgreSQL** là cơ sở dữ liệu chính (truy cập async qua `asyncpg`).
- Migration được quản lý bằng **Alembic** (`database/alembic/versions`).
- Model định nghĩa trong `database/models`, seed dữ liệu trong `database/seeds`.

## Kiến trúc & Cấu trúc thư mục

Dự án chia theo **module** (feature-based). Mỗi module là một thư mục độc lập trong `src/modules`, đóng gói đầy đủ logic của một nghiệp vụ. Một module điển hình gồm các loại file:

| File | Vai trò |
|------|---------|
| `*_services.py` | **Services** — chứa business logic, gọi xuống database/cache. |
| `*_routes.py` | **Route tổng** — gom (`include_router`) các route con (api + view) của module. |
| `*_apis.py` | **API routes** — các endpoint trả về JSON (CRUD, dữ liệu). |
| `views/*_views.py` | **View routes** — các endpoint render HTML bằng Jinja2 (HTMX/full page). |
| `*_schemas.py` | **Schemas** — Pydantic model cho request/response. |
| `*_constants.py` | **Constants** — hằng số, enum riêng của module. |
| `*_select.py` | **Select** — schema rút gọn dùng để chọn (project) một tập field cụ thể khi trả dữ liệu. |
| `views/*.j2` | Template Jinja2 của module. |

### Cấu trúc một module mẫu

Lấy module `events` làm ví dụ, một module được tổ chức như sau:

```
📁 events                       # 1 module = 1 nghiệp vụ
├── 🐍 event_routes.py          # ROUTE TỔNG — gom api + view router lại
├── 🐍 event_apis.py            # API routes  → trả JSON (CRUD)
├── 🐍 event_services.py        # SERVICES    → business logic, gọi DB/cache
├── 🐍 event_schemas.py         # SCHEMAS     → Pydantic request/response
├── 🐍 event_constants.py       # CONSTANTS   → hằng số / enum của module
├── 🐍 event_select.py          # SELECT      → schema rút gọn các field cần lấy
└── 📁 views                    # VIEW routes + template (HTML)
    ├── 📁 admin                # Khu vực quản trị
    │   ├── 🐍 admin_views.py   #   → route riêng cho admin
    │   └── 📄 *.j2             #   → template trang admin
    ├── 📁 main                 # Khu vực người dùng cuối
    │   ├── 🐍 main_views.py    #   → route riêng cho main
    │   └── 📄 *.j2             #   → template trang main
    └── 📄 *.j2                 # template dùng chung của module (cards, index...)
```

Luồng kết nối router: `admin_views.router` + `main_views.router` → gom trong `views` → `event_apis.router` + `views` → gom trong `event_routes.py` (file tổng) → đăng ký vào `src/modules/app_routes.py`.

> Lưu ý: thư mục `views` được tách thành hai khu vực **admin** và **main**, **mỗi khu vực có file route riêng** để phân quyền và dùng layout khác nhau.

### Tách `routes` thành tổng + api + view

Route tổng (`*_routes.py`) chỉ làm nhiệm vụ tập hợp, ví dụ với module `events`:

```python
# event_routes.py  — file tổng
from fastapi import APIRouter
from .views import event_views   # view routes (HTML)
from . import event_apis         # api routes (JSON)

router = APIRouter()
router.include_router(event_views.router)
router.include_router(event_apis.router)
```

- `event_apis.py` → các endpoint JSON (`create_event`, `get_events`, `get_event_by_id`, ...).
- `views/event_views.py` → các endpoint render HTML cho giao diện.

Tất cả router của các module được gom lại tại `src/modules/app_routes.py` rồi đăng ký vào app trong `src/main.py`.

### Phân tách `admin` và `main` trong `views`

Trong thư mục `views` của module, view được tách theo hai khu vực, **mỗi khu vực có file route riêng**:

- **admin** — giao diện quản trị (quản lý dữ liệu, CRUD), thường gắn tag `admin/<module>`.
- **main** — giao diện người dùng cuối (public/end-user).

Quy ước này cho phép phân quyền và bố trí layout riêng cho từng khu vực mà vẫn nằm trong cùng một module.

### Shared (dùng chung)

`src/shared` chứa thành phần tái sử dụng giữa các module:

- `base/` — lớp nền: `BaseRouter`, `BaseRequest`, `BaseRoute`, `base_crud`, `base_response`, `base_schema`, cấu hình Jinja toàn cục.
- `helpers/` — tiện ích (cbv, time, random, ...).
- `middlewares/` — middleware xác thực và xử lý exception.
- `schemas/` — schema dùng chung (phân trang, page).
- `services/` — service hạ tầng (Redis, Vercel Blob).
- `constants/` — hằng số dùng chung (cache tags, ...).

## Cây thư mục

```
├── 📁 database                  # Tầng dữ liệu
│   ├── 📁 alembic               # Migration
│   │   └── 📁 versions
│   ├── 📁 models                # SQLModel models (users, events, employees, files, ...)
│   ├── 📁 seeds                 # Seed dữ liệu
│   └── 🐍 db_config.py
├── 📁 src
│   ├── 📁 modules               # Các module nghiệp vụ
│   │   ├── 📁 authentication    # Đăng nhập, JWT, quên mật khẩu
│   │   ├── 📁 events            # Sự kiện (apis + views + services + schemas + constants)
│   │   ├── 📁 employees         # Nhân viên
│   │   ├── 📁 media_manager     # Quản lý media/file
│   │   ├── 📁 user              # Người dùng & phân quyền (role_constants)
│   │   └── 🐍 app_routes.py     # Gom router tất cả module
│   ├── 📁 shared                # Thành phần dùng chung (base, helpers, middlewares, services...)
│   ├── 📁 static                # CSS, JS (htmx, alpine, tiptap), public assets
│   ├── 📁 templates             # Layout, header/footer, components (editor), trang lỗi
│   ├── 📁 subscription_services # Cấu hình OpenAPI/Scalar
│   └── 🐍 main.py               # Khởi tạo FastAPI app
├── 📁 tests
├── ⚙️ environment.yml            # Định nghĩa môi trường conda + pip
├── 📄 Makefile                  # Lệnh tiện ích (dev, migrate, seed...)
├── ⚙️ alembic.ini
└── ⚙️ pyproject.toml             # Cấu hình ruff, pyright
```

## Bắt đầu

Các lệnh thường dùng (xem `Makefile`):

```bash
make install      # Tạo môi trường conda tại ./envs từ environment.yml
make dev          # Chạy server dev (python -m src.main)

# Database
make add_db m="msg"   # Tạo migration mới (autogenerate)
make update_db        # Apply migration mới nhất (upgrade head)
make reset_db         # Downgrade 1 bước
make seed             # Seed dữ liệu

make export_env       # Export lại environment.yml
make remove_cache     # Xóa __pycache__ / *.pyc
```

Cấu hình môi trường: tham khảo `.env.example`. Ở môi trường `dev`, tài liệu API (Scalar) được bật tự động.
