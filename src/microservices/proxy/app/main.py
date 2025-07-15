from http.client import HTTPException
import os
import random
import httpx
import logging
from fastapi import FastAPI, Request

app = FastAPI()


# Базовые адреса для backend-сервисов
MONOLITH_API_URL = os.environ.get("MONOLITH_URL")
MOVIE_SERVICE_URL = os.environ.get("MOVIES_SERVICE_URL")

# Управление миграцией через переменные окружения
GRADUAL_MIGRATION = os.getenv("GRADUAL_MIGRATION", "false").lower() == "true"
MOVIES_MIGRATION_PERCENT = int(os.getenv("MOVIES_MIGRATION_PERCENT", "0"))  # значение от 0 до 100

# Настройка логирования
logging.basicConfig(level=logging.INFO)

@app.get("/health")
async def health():
    return { "status": True }            

@app.get("/api/movies")
async def get_movies(request: Request):
    # Выбор сервиса на основе стратегии
    if GRADUAL_MIGRATION:
        roll = random.randint(1, 100)
        if roll <= MOVIES_MIGRATION_PERCENT:
            target_url = MOVIE_SERVICE_URL
            source = "movie-service"
        else:
            target_url = MONOLITH_API_URL
            source = "monolith"
    else:
        target_url = MONOLITH_API_URL
        source = "monolith (default)"

    proxied_url = f"{target_url}{request.url.path}"

    logging.info(f"Routing /api/movies to [{source}]: {proxied_url}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(proxied_url)
            response.raise_for_status()
            logging.info(f"Success [{response.status_code}] from {source}")
            return response.json()

    except httpx.HTTPStatusError as e:
        logging.warning(f"HTTP error from {source}: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

    except httpx.RequestError as e:
        logging.error(f"Request failed to {source}: {str(e)}")
        raise HTTPException(status_code=502, detail="Failed to reach backend service")
    
@app.get("/api/users")
async def get_movies(request: Request):
    if not MONOLITH_API_URL:
        raise HTTPException(status_code=500, detail="MONOLITH_API_URL not set")

    try:
        async with httpx.AsyncClient() as client:
            url = f"{MONOLITH_API_URL}{request.url.path}"
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    except httpx.RequestError as e:
        logging.warning(f"Request to monolith failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to reach monolith")

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)