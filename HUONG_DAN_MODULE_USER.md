# Phân tích module `user` — kiến trúc & luồng chạy

Đây là kiến trúc **layered (phân lớp)** khá chuẩn cho FastAPI + SQLModel. Trước khi "code tay", cần thấy rõ bức tranh tổng thể: 1 request đi qua bao nhiêu lớp, mỗi lớp làm nhiệm vụ gì.

## 1. Luồng của 1 request thật: `GET /api/User/profile`

```
Client → BaseRouter (định tuyến + gắn prefix /api)
       → clean_cbv (biến method trong class thành FastAPI route function)
       → RequireAuth (middleware: đọc token, xác thực, gắn user vào context)
       → UserApis.get_profile (controller, chỉ điều phối)
       → UserServices.get_raw_user (business logic)
       → RedisDep.get_or_set_async (cache trước, DB sau)
       → BaseCrud[Users].select(...).find_by_id(...) (query builder → SQL)
       → BaseResponse.ok(...) (chuẩn hóa JSON trả về)
```

Mở `src/modules/user/user_apis.py` sẽ thấy code rất ngắn — vì **toàn bộ độ phức tạp bị đẩy xuống các lớp base**. Đây vừa là điểm mạnh (code nghiệp vụ sạch) vừa là điểm khó cho người mới (phải hiểu ~5 lớp trừu tượng mới đọc được 10 dòng code).

## 2. Từng file trong `modules/user` làm gì

| File | Vai trò | Tương tự khái niệm chuẩn |
|---|---|---|
| `user_apis.py` | Controller — nhận request, gọi service, KHÔNG chứa logic nghiệp vụ | Controller trong MVC |
| `user_services.py` | Business logic: check trùng email, hash password, cache | Service layer |
| `user_select.py` | Định nghĩa **DTO đọc** (chỉ lấy cột cần thiết khi SELECT) | Read model / Projection |
| `user_schemas.py` | DTO trả ra ngoài (response shape) | Response DTO |
| `role_constants.py` | Enum vai trò | Constants/Enum |
| `user_routes.py` | Gộp router con (api + view) thành 1 router lớn | Route aggregator |
| `views/user_views.py` | Trả HTML (server-side render) thay vì JSON | View controller |

Điểm hay: `UserSelect` và `UserSchema` **giống hệt nhau về field**. Đây là chỗ dự án đang hơi dư thừa — một khi tự code, có thể gộp lại hoặc hiểu tại sao tách (select = cột lấy từ DB, schema = hình dạng trả cho client — về mặt lý thuyết tách ra để sau này 2 cái khác nhau vẫn không vỡ code).

## 3. Các lớp "phép thuật" (base) đứng sau

Đây là phần khiến code ngắn gọn nhưng khó hiểu nếu chưa từng thấy:

1. **`BaseRouter`** (`src/shared/base/base_route.py`) — tự sinh path: `.get_api("profile")` → `/api/User/profile`. Nó không phải FastAPI chuẩn, mà là lớp con tự thêm tiền tố.
2. **`clean_cbv`** (`src/shared/helpers/cbv.py`) — FastAPI gốc không hỗ trợ "class-based view" (viết method trong class rồi dùng `@router.get` như decorator). Đoạn này dùng `inspect` để "phẫu thuật" lại signature của hàm, chèn thêm tham số `Depends(cls)` — tức là biến `self` thành 1 dependency được FastAPI tự inject.
3. **`BaseCrud`** (`src/shared/base/base_crud.py`) — Generic Repository + Query Builder pattern, bọc quanh SQLModel/SQLAlchemy để không phải viết lại `select/where/join` thủ công mỗi service.
4. **`BaseResponse`** (`src/shared/base/base_response.py`) — chuẩn hóa mọi response về dạng `{success, status_code, message, data}`.
5. **`RequireAuth` / `AuthContext`** (`src/shared/middlewares/auth_middlewares.py`) — đọc Bearer token hoặc cookie, verify, so `token_version` để biết token có bị thu hồi không.

---

# Hướng dẫn code tay: xây lại từ số 0

Cách học tốt nhất là **không đọc code có sẵn rồi bắt chước** — mà **tự viết bản đơn giản, thiếu abstraction, rồi dần dần thêm vào** cho tới khi hiểu vì sao dự án cần từng lớp. Làm theo 5 bước sau, mỗi bước tự gõ code, đừng copy.

## Bước 1 — API "trần", không cbv, không base gì cả

```python
from fastapi import APIRouter, Depends
router = APIRouter()

@router.get("/api/user/profile")
async def get_profile():
    return {"success": True, "data": {"name": "demo"}}
```

Chạy được ngay. Đây là cách FastAPI "thô" hoạt động — cần nắm chắc cái này trước khi nhìn `BaseRouter`.

## Bước 2 — Tự thêm tầng Service (tách logic ra khỏi route)

```python
class UserServices:
    def __init__(self):
        self.fake_db = {"1": {"name": "demo"}}

    async def get_user(self, id: str):
        return self.fake_db.get(id)

@router.get("/api/user/profile")
async def get_profile(id: str, services: UserServices = Depends()):
    user = await services.get_user(id)
    if not user:
        return {"success": False, "message": "not found"}
    return {"success": True, "data": user}
```

→ Đây chính là lý do `UserApis` không có logic gì cả, chỉ gọi `self.services.xxx()`. Đây là ta vừa tự tái tạo pattern Controller/Service.

## Bước 3 — Tự viết `BaseResponse` mini (hiểu vì sao cần chuẩn hóa response)

Vấn đề: nếu 20 API viết `{"success":..., "data":...}` tay, dễ sai chính tả field, dễ quên field. Giải pháp: 1 class helper.

```python
class MyResponse:
    @staticmethod
    def ok(data=None, message="Success"):
        return {"success": True, "status_code": 200, "message": message, "data": data}

    @staticmethod
    def fail(message="Bad Request", status_code=400):
        from fastapi import HTTPException
        raise HTTPException(status_code=status_code, detail={"success": False, "message": message})
```

So sánh với `base_response.py` (`ok/created/fail/not_found/...`) — chỉ là các "preset" của cùng 1 ý tưởng. Không có gì huyền bí, chỉ là đặt tên cho các tổ hợp `status_code + success` hay dùng.

## Bước 4 — Tự viết CRUD generic mini (hiểu `BaseCrud`)

Đừng nhảy thẳng vào ~700 dòng của `base_crud.py`. Viết bản tí hon trước:

```python
from typing import TypeVar, Generic, Type
from sqlmodel import select

T = TypeVar("T")

class MiniCrud(Generic[T]):
    def __init__(self, session, model: Type[T]):
        self.session = session
        self.model = model

    async def find_by_id(self, id):
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.exec(stmt)
        return result.first()

    async def create(self, obj: T):
        self.session.add(obj)
        await self.session.commit()
        return obj
```

Dùng thử: `crud = MiniCrud(session, Users)` rồi `await crud.find_by_id(id)`.

Sau đó quay lại đọc `BaseCrud.select()` — nó làm y hệt việc vừa viết, cộng thêm 1 tính năng: nếu truyền vào 1 DTO class (như `UserSelect`) thay vì cột, nó tự soi field nào của DTO trùng tên cột trong bảng để chỉ SELECT đúng những cột đó (tối ưu, không lấy `password_hash` thừa). Đây gọi là "projection theo DTO" — một kỹ thuật hay nhưng không bắt buộc phải tự nghĩ ra, giờ đã biết lý do nó tồn tại.

## Bước 5 — `clean_cbv`: phần khó nhất, để cuối cùng

Vấn đề gốc: muốn viết:
```python
@clean_cbv(router)
class UserApis:
    def __init__(self, services: UserServices = Depends()):
        self.services = services

    @router.get_api("profile")
    async def get_profile(self):   # <-- có "self"!
        ...
```
Nhưng FastAPI **không biết `self` là gì** — nó chỉ biết inject tham số qua `Depends`, không biết "instance của class chứa hàm này". Nếu không sửa gì, khi gọi API sẽ lỗi vì FastAPI cố coi `self` là 1 query param bắt buộc.

`clean_cbv` giải quyết bằng cách:
1. Lấy signature gốc của `get_profile(self)`.
2. Bỏ `self` ra khỏi danh sách tham số "thấy được".
3. Thêm 1 tham số ẩn `__cbv_instance__: UserApis = Depends(UserApis)` — nghĩa là "trước khi gọi hàm, FastAPI hãy tự tạo 1 instance `UserApis` (gọi `__init__`, tự inject `services`), rồi coi nó chính là `self`".
4. Ghi đè `route.endpoint` bằng 1 hàm wrapper gọi `old_endpoint(instance, *args, **kwargs)`.

**Tự làm mini để hiểu**, không cần tổng quát như file thật:

```python
import inspect
from fastapi import Depends

def simple_cbv(router):
    def decorator(cls):
        for route in router.routes:
            old_fn = route.endpoint
            async def wrapper(*args, __inst__=Depends(cls), **kwargs):
                return await old_fn(__inst__, *args, **kwargs)
            route.endpoint = wrapper
            # (bản thật còn phải sửa lại __signature__ để FastAPI đọc đúng tham số)
        return cls
    return decorator
```

Nếu chỉ viết đến đây và chạy thử, sẽ thấy lỗi vì FastAPI đọc signature bằng `inspect`, không phải bằng cách gọi hàm — nó cần biết *khai báo* tham số là gì trước khi request tới. Đó là lý do bản thật (`cbv.py`) có dòng:
```python
setattr(wrapper, "__signature__", sig.replace(parameters=new_params + [cbv_param]))
```
— tự "giả mạo" signature để FastAPI đọc đúng. Đây chính là chỗ code tay khó nhất trong cả module, và giờ đã hiểu **why**, không chỉ **what**.

---

# Bài tập để luyện tay thật sự

Đề xuất theo thứ tự tăng dần, dùng lại hạ tầng có sẵn của dự án (không cần viết lại base):

1. Thêm API `PUT /api/User/profile` để user tự sửa `name`. Tự viết: 1 schema `UpdateProfileRequest` (kế thừa `BaseSchema`), 1 method `update_profile` trong `UserServices` dùng `self.crud.update(id=..., data=...)`, 1 route trong `UserApis` dùng `RequireAuth()`.
2. Khi update xong, phải **xóa cache** (`CacheTags.USER`) — tìm cách `RedisDep` cung cấp để invalidate, vì `get_raw_user` đang cache theo `id`. Đây là bug tiềm ẩn thật trong flow hiện tại nếu không để ý.
3. Viết 1 route mới hoàn toàn không dùng `clean_cbv` (dùng function thường như Bước 1), rồi so sánh dòng code — để cảm nhận rõ cbv tiết kiệm được gì và đánh đổi gì (khó debug hơn vì stack trace đi qua wrapper).
