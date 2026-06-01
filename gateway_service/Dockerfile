FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

COPY gateway_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY gateway_service/app ./app
COPY kafka_service ./kafka_service

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
