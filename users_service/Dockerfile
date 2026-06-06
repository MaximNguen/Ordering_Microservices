FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Устанавливаем netcat для проверки готовности БД
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

COPY users_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY users_service/alembic.ini ./
COPY users_service/migrations ./migrations
COPY users_service/app ./app
COPY users_service/config.py ./config.py

# Скрипт ожидания БД и запуска миграций
RUN printf '#!/bin/bash\n\
set -e\n\
\n\
# Ждем БД\n\
echo "Waiting for database users-db:5432..."\n\
while ! nc -z users-db 5432; do\n\
  sleep 0.5\n\
done\n\
echo "Database ready"\n\
\n\
# Запускаем миграции\n\
alembic upgrade head\n\
\n\
# Запускаем приложение\n\
exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000\n\
' > /start.sh && chmod +x /start.sh

CMD ["/start.sh"]