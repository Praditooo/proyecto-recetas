from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401  (registra los modelos en Base.metadata)
from app.database import Base, engine
from app.routers import auth, ingredients, recipes, web

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    # TODO(equipo): reemplazar create_all por migraciones con Alembic.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Generador de Recetas con Inventario e IA",
    description="API para gestionar un inventario de ingredientes y generar recetas con un LLM.",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(auth.router)
app.include_router(ingredients.router)
app.include_router(recipes.router)
app.include_router(web.router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(BASE_DIR / "static" / "favicon.ico")


@app.get("/health", tags=["sistema"])
def health():
    return {"status": "ok"}
