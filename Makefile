# ==============================================================================
# 1. NHẬN DIỆN HỆ ĐIỀU HÀNH & ĐỊNH NGHĨA BIẾN
# ==============================================================================
ifeq ($(OS),Windows_NT)
	# Cấu hình cho Windows
	PROJECT_PATH := $(subst \,/,$(CURDIR))
	PYTHON := $(PROJECT_PATH)/envs/python.exe
	PIP := $(PROJECT_PATH)/envs/Scripts/pip.exe
	
	# Lệnh lọc loại bỏ dòng chứa "prefix:" và "name:"
	FILTER_CMD := findstr /V /C:"prefix:" /C:"name:"
	
	RM_ENVS_CMD := if exist envs (rd /s /q envs)
	ECHO_OS := Windows
else
	# Cấu hình cho Linux / macOS
	PROJECT_PATH := $(shell pwd)
	PYTHON := $(PROJECT_PATH)/envs/bin/python
	PIP := $(PROJECT_PATH)/envs/bin/pip
	
	# Lệnh lọc loại bỏ dòng chứa "prefix:" và "name:" (bỏ dấu ^ để bắt rộng hơn)
	FILTER_CMD := grep -vE "prefix:|name:"
	
	RM_ENVS_CMD := rm -rf envs
	ECHO_OS := Linux/macOS
endif

ENV_PATH := $(PROJECT_PATH)/envs

# ==============================================================================
# 2. CÁC TARGETS (LỆNH THỰC THI)
# ==============================================================================

install:
	conda create --file environment.yml --prefix ./envs

uv-install:
	uv venv ./envs --python 3.14
	source ./envs/bin/activate
	uv pip install -r requirements.txt

dev:
	python -m src.main

granian:
	set -a; \
	source <(grep -v '^#' .env | tr -d '\r'); \
	set +a; \
	granian --interface asgi --loop uvloop --workers 4 --port $$PORT src.main:app

granian-dev:
	set -a; \
	source <(grep -v '^#' .env | tr -d '\r'); \
	set +a; \
	granian --interface asgi --loop uvloop --reload --reload-paths src --port $$PORT src.main:app

update_env:
	conda env update --prefix $(ENV_PATH) --file environment.yml --prune

export_env:
	@conda env export --prefix $(ENV_PATH) --no-builds | $(FILTER_CMD) > environment.yml

export_vercel:
	pip freeze > requirements.txt

clean:
	@echo "Dang xoa moi truong tren $(ECHO_OS)..."
	@$(RM_ENVS_CMD)
	@echo "Da xoa xong!"

clean_cache:
	conda clean --all --yes

reset_db:
	alembic downgrade -1

remove:
	alembic downgrade base

update_db:
	alembic upgrade head

add_db:
	alembic revision --autogenerate -m "$(m)"

seed:
	python -m database.seeds.seed_db

remove_cache:
	python -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [p.unlink(missing_ok=True) for p in pathlib.Path('.').rglob('*.py[co]')]"