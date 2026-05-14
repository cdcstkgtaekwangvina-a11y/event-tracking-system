# File Tree: check in app

```
├── 📁 database
│   ├── 📁 alembic
│   │   ├── 📁 versions
│   │   │   └── 🐍 3f8cecf569a6_init_db.py
│   │   ├── 📄 README
│   │   ├── 🐍 env.py
│   │   └── 📄 script.py.mako
│   ├── 📁 models
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 app_db.py
│   │   ├── 🐍 base_model.py
│   │   ├── 🐍 employees.py
│   │   ├── 🐍 events.py
│   │   ├── 🐍 events_employees.py
│   │   └── 🐍 users.py
│   ├── 📁 seeds
│   │   └── 🐍 __init__.py
│   ├── 🐍 __init__.py
│   └── 🐍 db_config.py
├── 📁 src
│   ├── 📁 middlewares
│   │   └── 🐍 __init__.py
│   ├── 📁 modules
│   │   ├── 📁 authentication
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 auth_routes.py
│   │   │   ├── 🐍 auth_services.py
│   │   │   └── 🐍 auth_shemas.py
│   │   ├── 📁 events
│   │   │   ├── 📁 views
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   └── 📄 index.j2
│   │   │   ├── 🐍 event_constants.py
│   │   │   ├── 🐍 event_routes.py
│   │   │   ├── 🐍 event_schemas.py
│   │   │   └── 🐍 event_services.py
│   │   ├── 📁 user
│   │   │   ├── 🐍 __init__.py
│   │   │   └── 🐍 role_constants.py
│   │   ├── 🐍 __init__.py
│   │   └── 🐍 app_routes.py
│   ├── 📁 shared
│   │   ├── 📁 base
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 base_crud.py
│   │   │   └── 🐍 base_response.py
│   │   ├── 📁 helpers
│   │   │   ├── 🐍 __init__.py
│   │   │   └── 🐍 time_extensions.py
│   │   ├── 📁 schemas
│   │   │   ├── 🐍 __init__.py
│   │   │   └── 🐍 pagination_schemas.py
│   │   └── 🐍 __init__.py
│   ├── 📁 static
│   │   ├── 📁 css
│   │   ├── 📁 js
│   │   │   └── 📄 fetch_helper.js
│   │   ├── 📁 media
│   │   └── 📄 index.j2
│   ├── 📁 subscription_services
│   │   ├── 🐍 __init__.py
│   │   └── 🐍 subscription_openapi.py
│   └── 🐍 main.py
├── 📁 tests
│   └── 🐍 __init__.py
├── ⚙️ .env.example
├── ⚙️ .gitignore
├── 📄 Makefile
├── 📝 README.md
├── ⚙️ alembic.ini
├── ⚙️ environment.yml
└── ⚙️ pyproject.toml
```
