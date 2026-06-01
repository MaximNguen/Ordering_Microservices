FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY users_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY users_service/alembic.ini ./
COPY users_service/migrations ./migrations
COPY users_service/app ./app
COPY users_service/config.py ./config.py

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
