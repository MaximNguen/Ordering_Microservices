import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

import httpx
import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status


def _find_file_handler(logger: logging.Logger, log_file: Path) -> RotatingFileHandler | None:
    target = log_file.resolve()
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler):
            try:
                if Path(handler.baseFilename).resolve() == target:
                    return handler
            except OSError:
                continue
    return None


def _configure_logging() -> None:
    log_dir = Path(os.getenv("LOG_DIR", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "gateway_service.log"

    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    max_bytes = int(os.getenv("LOG_MAX_BYTES", "1000000"))
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", "3"))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    file_handler = _find_file_handler(root_logger, log_file)
    if file_handler is None:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root_logger.addHandler(file_handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.setLevel(log_level)
        if not uvicorn_logger.propagate and _find_file_handler(uvicorn_logger, log_file) is None:
            uvicorn_logger.addHandler(file_handler)


_configure_logging()
logger = logging.getLogger(__name__)

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL", "http://localhost:8000").rstrip("/")
DELIVERY_SERVICE_URL = os.getenv("DELIVERY_SERVICE_URL", "http://localhost:8001").rstrip("/")
ORDERS_SERVICE_URL = os.getenv("ORDERS_SERVICE_URL", "http://localhost:8002").rstrip("/")
PRODUCTS_SERVICE_URL = os.getenv("PRODUCTS_SERVICE_URL", "http://localhost:8003").rstrip("/")
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
CHECK_USER_STATUS = os.getenv("CHECK_USER_STATUS", "true").lower() == "true"
INTERNAL_CALL_HEADER = os.getenv("INTERNAL_CALL_HEADER", "X-Internal-Call")
INTERNAL_CALL_VALUE = os.getenv("INTERNAL_CALL_VALUE", "true")

HOP_BY_HOP_HEADERS = {"connection", "transfer-encoding", "content-length"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=10.0)
    yield
    await app.state.http.aclose()

app = FastAPI(title="API Gateway", lifespan=lifespan)


def _filter_headers(headers: httpx.Headers) -> dict:
    return {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}


def _get_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_header.split(" ", 1)[1].strip()


async def _check_user_status(request: Request, token: str) -> None:
    if not CHECK_USER_STATUS:
        return
    users_url = f"{USERS_SERVICE_URL}/users/me"
    response = await request.app.state.http.get(
        users_url,
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code == status.HTTP_200_OK:
        return
    if response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not authorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Users service unavailable",
    )


async def require_access_token(request: Request) -> dict:
    if request.headers.get(INTERNAL_CALL_HEADER, "").lower() == INTERNAL_CALL_VALUE.lower():
        return {"internal": True}
    token = _get_bearer_token(request)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type = payload.get("token_type")
        if token_type != "access":
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

    await _check_user_status(request, token)
    return payload


async def _proxy_request(request: Request, base_url: str) -> Response:
    url = httpx.URL(f"{base_url}{request.url.path}").copy_with(query=request.url.query)
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    body = await request.body()

    response = await request.app.state.http.request(
        request.method,
        url,
        headers=headers,
        content=body,
    )

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=_filter_headers(response.headers),
        media_type=response.headers.get("content-type"),
    )


@app.api_route("/users", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@app.api_route("/users/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def users_proxy(request: Request):
    return await _proxy_request(request, USERS_SERVICE_URL)


@app.api_route(
    "/deliveries", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], dependencies=[Depends(require_access_token)]
)
@app.api_route(
    "/deliveries/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    dependencies=[Depends(require_access_token)],
)
async def deliveries_proxy(request: Request):
    return await _proxy_request(request, DELIVERY_SERVICE_URL)


@app.api_route(
    "/orders", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], dependencies=[Depends(require_access_token)]
)
@app.api_route(
    "/orders/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    dependencies=[Depends(require_access_token)],
)
async def orders_proxy(request: Request):
    return await _proxy_request(request, ORDERS_SERVICE_URL)


@app.api_route(
    "/products", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], dependencies=[Depends(require_access_token)]
)
@app.api_route(
    "/products/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    dependencies=[Depends(require_access_token)],
)
async def products_proxy(request: Request):
    return await _proxy_request(request, PRODUCTS_SERVICE_URL)


@app.get("/")
async def root():
    return {"message": "Gateway работает"}
