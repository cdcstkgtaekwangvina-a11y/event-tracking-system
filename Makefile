install:
	conda create --file environment.yml --prefix ./envs

ifeq ($(OS),Windows_NT)
    PROJECT_PATH := $(subst \,/,$(CURDIR))
    PYTHON := $(PROJECT_PATH)/envs/python.exe
    PIP := $(PROJECT_PATH)/envs/Scripts/pip.exe
else
    PROJECT_PATH := $(shell pwd)
    PYTHON := $(PROJECT_PATH)/envs/bin/python
    PIP := $(PROJECT_PATH)/envs/bin/pip
endif

dev:
	python -m src.main

ifeq ($(OS),Windows_NT)
    PROJECT_PATH := $(subst \,/,$(CURDIR))
else
    PROJECT_PATH := $(shell pwd)
endif

ENV_PATH := $(PROJECT_PATH)/envs

update_env:
	conda env update --prefix $(ENV_PATH) --file environment.yml --prune

export_env:
	@conda env export --prefix $(ENV_PATH) --no-builds | findstr /V /B "prefix: name:" > environment.yml

export_vercel:
	pip freeze > requirements.txt

clean:
ifeq ($(OS),Windows_NT)
	@echo "Dang xoa moi truong tren Windows..."
	@if exist envs (rd /s /q envs)
else
	@echo "Dang xoa moi truong tren Linux/macOS..."
	rm -rf envs
endif
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
	python -c "import pathlib, shutil; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]"


	