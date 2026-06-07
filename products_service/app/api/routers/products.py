import uuid
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.dependencies import get_product_service
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.products import ProductService

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
bearer_scheme = HTTPBearer(auto_error=False)
INTERNAL_CALL_HEADER = os.getenv("INTERNAL_CALL_HEADER", "X-Internal-Token")
INTERNAL_CALL_TOKEN = os.getenv("INTERNAL_CALL_TOKEN", "")
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


def require_service_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> None:
    if INTERNAL_CALL_TOKEN and request.headers.get(INTERNAL_CALL_HEADER) == INTERNAL_CALL_TOKEN:
        return
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth is not configured",
        )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("token_type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

router = APIRouter(
    prefix="/products",
    tags=["products"],
    dependencies=[Depends(require_service_auth)],
)


@router.get("/", response_model=list[ProductResponse], status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def get_all_products(
    skip: int = 0,
    limit: int = 100,
    product_service: ProductService = Depends(get_product_service),
):
    """Return all products with pagination."""
    results = await product_service.get_all_products(skip=skip, limit=limit)
    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Products not found")
    return results


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_product(
    product_create: ProductCreate,
    product_service: ProductService = Depends(get_product_service),
):
    """Create a new product from request data."""
    product = await product_service.create_product(product_create)
    if not product:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create product")
    return product


@router.get("/{product_id}", response_model=ProductResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def get_product(
    product_id: uuid.UUID,
    product_service: ProductService = Depends(get_product_service),
):
    """Return product details by ID."""
    product = await product_service.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def update_product(
    product_id: uuid.UUID,
    product_update: ProductUpdate,
    product_service: ProductService = Depends(get_product_service),
):
    """Update product details by ID."""
    updated_product = await product_service.update_product(product_id, product_update)
    if not updated_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return updated_product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_product(
    product_id: uuid.UUID,
    product_service: ProductService = Depends(get_product_service),
):
    """Delete product by ID."""
    deleted = await product_service.delete_product(product_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
