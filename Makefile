# ==============================================================================
# 1. CẤU HÌNH MÔI TRƯỜNG & BIẾN
# ==============================================================================
-include .env
export

ENV_DIR := envs

ifeq ($(OS),Windows_NT)
    PYTHON := $(ENV_DIR)/Scripts/python.exe
    PIP := $(ENV_DIR)/Scripts/pip.exe
    RM_DIR := if exist $(ENV_DIR) rd /s /q $(ENV_DIR)
    FILTER_CMD := findstr /V /C:"prefix:" /C:"name:"
else
    PYTHON := $(ENV_DIR)/bin/python
    PIP := $(ENV_DIR)/bin/pip
    RM_DIR := rm -rf $(ENV_DIR)
    FILTER_CMD := grep -vE "prefix:|name:"
endif

.PHONY: install uv-install dev granian granian-dev update_env export_env \
        export_vercel clean clean_cache update_db add_db reset_db remove_db seed remove_cache

# ==============================================================================
# 2. CHẠY ỨNG DỤNG
# ==============================================================================
dev:
	$(PYTHON) -m src.main

granian:
	exec granian --interface asgi --loop uvloop --workers 4 --port $${PORT:-8000} src.main:app

granian-dev:
	WATCHFILES_FORCE_POLLING=true exec granian --interface asgi --loop uvloop --reload --reload-paths src --port $${PORT:-8000} src.main:app

# ==============================================================================
# 3. QUẢN LÝ MÔI TRƯỜNG & PHỤ THUỘC
# ==============================================================================
install:
	conda create --file environment.yml --prefix ./$(ENV_DIR)

uv-install:
	uv venv ./$(ENV_DIR) --python 3.14
	uv pip install -r requirements.txt --python ./$(ENV_DIR)

update_env:
	conda env update --prefix ./$(ENV_DIR) --file environment.yml --prune

export_env:
	@conda env export --prefix ./$(ENV_DIR) --no-builds | $(FILTER_CMD) > environment.yml

export_vercel:
	$(PIP) freeze > requirements.txt

# ==============================================================================
# 4. QUẢN LÝ CƠ SỞ DỮ LIỆU
# ==============================================================================
update_db:
	alembic upgrade head

add_db:
	alembic revision --autogenerate -m "$(m)"

reset_db:
	alembic downgrade -1

remove_db:
	alembic downgrade base

seed:
	$(PYTHON) -m database.seeds.seed_db

# ==============================================================================
# 5. DỌN DẸP
# ==============================================================================
clean:
	@echo "Xoa môi trường venv..."
	@$(RM_DIR)

clean_cache:
	conda clean --all --yes

remove_cache:
	$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [p.unlink(missing_ok=True) for p in pathlib.Path('.').rglob('*.py[co]')]"