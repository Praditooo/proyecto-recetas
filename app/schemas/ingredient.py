from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


ALLOWED_UNITS: list[str] = [
    "unidad", "g", "kg", "mg", "oz", "lb",
    "ml", "l", "taza", "cucharada", "cucharadita",
    "litro", "pieza", "rebanada", "diente", "manojo",
    "pizca", "lata", "paquete", "sobre",
]


class IngredientBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    quantity: float = Field(gt=0, le=100_000)
    unit: str = Field(default="unidad", min_length=1, max_length=20)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("El nombre no puede estar vacío")
        return value

    @field_validator("unit")
    @classmethod
    def normalize_unit(cls, value: str) -> str:
        value = " ".join(value.split()).lower()
        if not value:
            raise ValueError("La unidad no puede estar vacía")
        if value not in ALLOWED_UNITS:
            raise ValueError(
                f"Unidad no permitida: '{value}'. "
                f"Las unidades válidas son: {', '.join(ALLOWED_UNITS)}"
            )
        return value


class IngredientCreate(IngredientBase):
    pass


class IngredientUpdate(IngredientBase):
    pass


class IngredientOut(IngredientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
