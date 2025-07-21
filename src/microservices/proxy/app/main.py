from http.client import HTTPException
import os
import random
import httpx
import logging
from fastapi import FastAPI, Request
from fastapi.responses import Response
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

@app.api_route("/api/movies", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_movies(request: Request):
    # Определение назначения
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
    method = request.method
    headers = dict(request.headers)
    body = await request.body()

    logging.info(f"{method} /api/movies → {source} → {proxied_url}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=proxied_url,
                content=body,
                headers=headers
            )

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type")
        )

    except httpx.HTTPStatusError as e:
        logging.warning(f"HTTP error from {source}: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

    except httpx.RequestError as e:
        logging.error(f"Request failed to {source}: {str(e)}")
        raise HTTPException(status_code=502, detail="Failed to reach backend service")
    
@app.api_route("/api/users", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_users(request: Request):
    if not MONOLITH_API_URL:
        raise HTTPException(status_code=500, detail="MONOLITH_API_URL not set")

    target_url = f"{MONOLITH_API_URL}{request.url.path}"
    method = request.method
    headers = dict(request.headers)
    body = await request.body()

    logging.info(f"{method} /api/users → monolith → {target_url}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=target_url,
                content=body,
                headers=headers
            )

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type")
        )

    except httpx.RequestError as e:
        logging.warning(f"Request to monolith failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to reach monolith")

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)