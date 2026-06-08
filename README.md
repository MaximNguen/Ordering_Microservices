# 🚀 Микросервисная платформа электронной коммерции

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Kafka](https://img.shields.io/badge/Apache%20Kafka-3.6+-231F20.svg)](https://kafka.apache.org/)
[![Redis](https://img.shields.io/badge/Redis-7.2-DC382D.svg)](https://redis.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-26+-2496ED.svg)](https://www.docker.com/)

**Готовое к продакшену микросервисное решение** для интернет-магазина с асинхронным взаимодействием, распределённым кешированием и полноценной наблюдаемостью.

---

## ✨ Что умеет проект

| Функциональность | Описание |
|------------------|----------|
| 👤 **Управление пользователями** | Регистрация, авторизация, JWT токены (Access/Refresh), роли (покупатель, продавец, курьер, админ) |
| 📦 **Управление заказами** | Создание, изменение статуса, проверка наличия товаров через API Gateway |
| 🚚 **Сервис доставки** | Создание доставки, отслеживание статуса, назначение курьера |
| 🛒 **Товарный каталог** | CRUD операции, управление ассортиментом |
| 🔌 **API Gateway** | Единая точка входа, маршрутизация, аутентификация, rate limiting |
| 📡 **Асинхронное взаимодействие** | Синхронные запросы через Kafka с ожиданием ответа (Request-Response) |
| 💾 **Распределённое кеширование** | Redis с автоматической инвалидацией по событиям |
| 📊 **Мониторинг** | Prometheus метрики (запросы, БД, Kafka сообщения) |
| 🐳 **Полная контейнеризация** | Docker Compose с 8+ сервисами |

---

## 🧠 Технологии и паттерны

### Архитектурные паттерны

| Паттерн | Применение |
|---------|------------|
| **API Gateway** | Единая точка входа с проверкой токенов и маршрутизацией |
| **Database per Service** | У каждого сервиса своя PostgreSQL БД |
| **Event-Driven Architecture** | Kafka для асинхронной коммуникации |
| **Request-Response по Kafka** | Gateway шлёт запрос → сервис отвечает в тот же топик |
| **Repository + Service** | Чистое разделение логики доступа к данным и бизнес-логики |
| **Dependency Injection** | FastAPI Depends + ручное внедрение |
| **Cache-Aside** | Чтение через кеш с обновлением при изменении |
| **Cache Invalidation by Event** | Redis Pub/Sub для сброса кеша при изменении данных |

### Используемый стек
| Часть проекта | Технологии и инструменты |
|---------|------------|
| Backend | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) |
| БД | PostgreSQL 16 (по отдельной БД на сервис) |
| Очереди | Apache Kafka, aiokafka |
| Кеширование | Redis (redis-py, асинхронно) |
| Мониторинг | Prometheus, prometheus-fastapi-instrumentator |
| Контейнеры | Docker, Docker Compose |
| Логирование | RotatingFileHandler, структурированные логи |
| Аутентификация | JWT (HS256), bcrypt |
