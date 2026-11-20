# Generador de recetas con inventario e IA

Aplicación web (FastAPI + PostgreSQL) donde cada usuario administra su inventario de ingredientes y genera recetas con un LLM. El LLM está encapsulado en `app/services/llm_service.py`: recibe el inventario y devuelve un JSON validado (nombre del plato, ingredientes con cantidades, pasos, tiempo estimado y dificultad). No existe ningún chat ni conversación libre.

## Estructura

```
proyecto-recetas/
├── app/
│   ├── main.py              # Instancia FastAPI, routers, estáticos, favicon
│   ├── config.py            # Variables de entorno (pydantic-settings)
│   ├── database.py          # Engine, sesión y Base de SQLAlchemy
│   ├── security.py          # bcrypt + JWT
│   ├── deps.py              # Dependencias: sesión de BD y usuario actual
│   ├── models/              # users, ingredients, recipes, ratings
│   ├── schemas/             # Validación Pydantic (entrada/salida y contrato del LLM)
│   ├── routers/             # auth, ingredients, recipes, web (HTML)
│   ├── services/llm_service.py
│   └── templates/           # Jinja2: base, index (acceso), dashboard
├── static/                  # favicon.ico, style.css, js/ (common, inventory, recipes)
├── tests/                   # pytest (16 funciones de prueba)
├── Dockerfile · docker-compose.yml · Caddyfile
├── .env.example · pytest.ini · requirements.txt
```

## Ejecución local con Docker

```bash
cp .env.example .env        # completa SECRET_KEY, contraseña de BD y LLM_API_KEY
docker compose up --build
```

- Aplicación: http://localhost:8000
- Documentación Swagger: http://localhost:8000/docs (botón **Authorize** con correo y contraseña)

## Ejecución local sin Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # descomenta DATABASE_URL y apunta a tu PostgreSQL
uvicorn app.main:app --reload
```

## Pruebas

```bash
pytest
```

Las pruebas usan SQLite en memoria y un LLM simulado: no necesitan base de datos real ni API key.

## API

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/auth/register` | Registro |
| POST | `/api/auth/login` | Inicio de sesión (devuelve JWT) |
| GET | `/api/auth/me` | Usuario actual |
| GET/POST | `/api/ingredients` | Listar / crear ingredientes |
| PUT/DELETE | `/api/ingredients/{id}` | Editar / eliminar ingrediente |
| POST | `/api/recipes/generate` | Generar receta con el inventario actual |
| GET | `/api/recipes` · `/api/recipes/{id}` | Historial / detalle |
| POST | `/api/recipes/{id}/rating` | Calificar de 1 a 5 estrellas |
| DELETE | `/api/recipes/{id}` | Eliminar del historial |

## Despliegue en un VPS con dominio y HTTPS

1. Crea un registro DNS **A** del dominio hacia la IP del VPS y abre los puertos 80 y 443.
2. Instala Docker y Docker Compose en el servidor y clona el repositorio.
3. Crea `.env` desde `.env.example` con valores reales (`DOMAIN`, `SECRET_KEY`, contraseña de BD, `LLM_API_KEY`).
4. Ejecuta `docker compose --profile prod up -d --build`.

Caddy (perfil `prod`) obtiene y renueva el certificado de Let's Encrypt automáticamente. Si prefieres Certbot, elimina el servicio `caddy` y configura Nginx como proxy hacia `app:8000`.

## Seguridad

- `.env` está en `.gitignore`; solo se versiona `.env.example`, sin valores reales.
- Contraseñas con bcrypt; tokens JWT firmados con `SECRET_KEY`.
- Cada consulta filtra por el usuario autenticado (nadie ve datos ajenos).
- El contenido generado por el LLM se valida con Pydantic y se muestra con `textContent`, nunca como HTML.

## Reparto de trabajo sugerido

Cada área tiene archivos propios para que los integrantes avancen sin conflictos de merge. Ajusta la cantidad de áreas al tamaño del equipo.

| Área | Archivos principales | Ideas para los commits |
|---|---|---|
| A. Autenticación y seguridad | `routers/auth.py`, `security.py`, `deps.py`, `models/user.py`, `schemas/user.py`, `tests/test_auth_api.py`, `templates/index.html` | Reglas de contraseña, expiración y refresh de token, límite de intentos, más pruebas |
| B. Inventario | `routers/ingredients.py`, `models/ingredient.py`, `schemas/ingredient.py`, `static/js/inventory.js`, `tests/test_ingredients_api.py`, `tests/test_ingredient_validation.py` | Unidades predefinidas, búsqueda, fusión de duplicados, edición en línea |
| C. LLM y generación | `services/llm_service.py`, `routers/recipes.py` (`/generate`), `schemas/recipe.py`, `tests/test_llm_*.py` | Mejorar el prompt, reintentos, preferencias de dieta, tiempo máximo, pruebas con respuestas reales anonimizadas |
| D. Historial, calificaciones y despliegue | `routers/recipes.py` (resto), `models/recipe.py`, `models/rating.py`, `static/js/recipes.js`, `static/style.css`, `Dockerfile`, `docker-compose.yml`, `Caddyfile`, `README.md`, `tests/test_recipes_api.py` | Filtros y paginación del historial, promedio de calificaciones, Alembic, despliegue y documentación |

Flujo de Git recomendado: una rama por tarea (`feat/inventario-edicion`), commits pequeños con mensajes descriptivos (`feat: valida unidad del ingrediente`), pull request con revisión de otro integrante y `main` siempre estable.

## Pendientes conocidos

- Reemplazar `create_all` por migraciones con Alembic (ver `app/main.py`).
- Confirmar que el modelo configurado en `LLM_MODEL` siga disponible en el proveedor elegido.
- Los endpoints son síncronos salvo la generación; si la carga crece, migrar a sesiones asíncronas.
