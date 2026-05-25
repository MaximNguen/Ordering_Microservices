from pydantic import BaseModel, ConfigDict
import uuid
    
class ProductCreateSchema(BaseModel):
    """Схема для создания нового продукта, определяющая необходимые поля и их типы."""
    model_config = ConfigDict(from_attributes=True)
    name: str
    description: str | None = None
    price: float

class ProductUpdateSchema(BaseModel):
    """Схема для обновления существующего продукта, определяющая поля, которые могут быть изменены."""
    model_config = ConfigDict(from_attributes=True)
    name: str | None = None
    description: str | None = None
    price: float | None = None
    
class ProductResponseSchema(BaseModel):
    """Схема для ответа API, содержащая информацию о продукте."""
    model_config = ConfigDict(from_attributes=True)
    product_id: uuid.UUID
    name: str
    description: str | None
    price: float