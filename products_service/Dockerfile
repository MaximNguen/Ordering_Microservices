FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY products_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY products_service/alembic.ini ./
COPY products_service/migrations ./migrations
COPY products_service/app ./app

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8003"]
