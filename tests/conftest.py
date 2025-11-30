import os
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine, MetaData


# Создаем временную директорию для тестовой БД в текущей директории проекта
# Это более надежно, чем использовать TEMP
TEST_DB_DIR = Path(__file__).parent.parent / "test_db_temp"
TEST_DB_DIR.mkdir(parents=True, exist_ok=True)
TEST_DB_PATH = TEST_DB_DIR / "test_app.db"

# Удаляем старую базу, если существует
if TEST_DB_PATH.exists():
    try:
        TEST_DB_PATH.unlink()
    except Exception:
        pass

# Формируем правильный путь для SQLite
# Используем абсолютный путь и заменяем обратные слеши для Windows
db_path_abs = str(TEST_DB_PATH.absolute())
if os.name == "nt":  # Windows
    # Для SQLite на Windows нужны прямые слеши в URL
    db_path_abs = db_path_abs.replace("\\", "/")

# Создаем два URL:
# 1. Синхронный для создания схемы (для metadata.create_all/drop_all)
SYNC_DB_URL = f"sqlite:///{db_path_abs}"
# 2. Асинхронный для работы с базой данных через databases
ASYNC_DB_URL = f"sqlite+aiosqlite:///{db_path_abs}"

# Устанавливаем переменную окружения для подключения к тестовой БД
# Используем асинхронный URL для Database
os.environ["FASTAPI_DB_URL"] = ASYNC_DB_URL

from main import app  # noqa: E402
from models.db import metadata, db  # noqa: E402
# Импортируем модели, чтобы таблицы зарегистрировались в metadata
from models import models  # noqa: E402, F401

# Создаем синхронный engine для создания/удаления схемы
sync_engine = create_engine(SYNC_DB_URL, future=True)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_database():
    """Очищает тестовую базу данных после всех тестов"""
    yield
    # Закрываем синхронный engine
    try:
        sync_engine.dispose()
    except Exception:
        pass
    # Удаляем файл базы данных после тестов
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass
    # Пытаемся удалить директорию
    if TEST_DB_DIR.exists():
        try:
            TEST_DB_DIR.rmdir()
        except OSError:
            pass


@pytest_asyncio.fixture(scope="function")
async def reset_schema():
    """Создает и очищает схему базы данных перед каждым тестом"""
    # Сначала удаляем существующие таблицы (если они есть)
    # Используем синхронный engine для создания схемы
    try:
        metadata.drop_all(sync_engine)
    except Exception:
        pass
    # Создаем таблицы заново
    metadata.create_all(sync_engine)
    yield
    # Очищаем после теста
    try:
        metadata.drop_all(sync_engine)
    except Exception:
        pass


@pytest_asyncio.fixture(scope="function")
async def client(reset_schema):
    """Создает тестового клиента с подключенной базой данных"""
    # Подключаемся к базе данных перед каждым тестом
    await db.connect()
    try:
        async with AsyncClient(app=app, base_url="http://testserver") as test_client:
            yield test_client
    finally:
        # Отключаемся от базы данных после теста
        try:
            await db.disconnect()
        except Exception:
            pass

