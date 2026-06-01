FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY orders_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY orders_service/alembic.ini ./
COPY orders_service/migrations ./migrations
COPY orders_service/app ./app

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8002"]
