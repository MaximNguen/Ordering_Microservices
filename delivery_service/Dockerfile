FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY delivery_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY delivery_service/alembic.ini ./
COPY delivery_service/migrations ./migrations
COPY delivery_service/app ./app

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8001"]
