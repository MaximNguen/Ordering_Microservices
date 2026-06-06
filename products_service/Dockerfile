FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

COPY products_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY products_service/alembic.ini ./
COPY products_service/migrations ./migrations
COPY products_service/app ./app

RUN printf '#!/bin/bash\n\
set -e\n\
echo "Waiting for database products-db:5432..."\n\
while ! nc -z products-db 5432; do\n\
  sleep 0.5\n\
done\n\
echo "Database ready"\n\
alembic upgrade head\n\
exec uvicorn app.api.main:app --host 0.0.0.0 --port 8003\n\
' > /start.sh && chmod +x /start.sh

CMD ["/start.sh"]