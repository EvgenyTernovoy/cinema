from datetime import datetime
import os
import logging
from typing import Any, List, Optional
from fastapi import FastAPI, Request
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import asyncio
from pydantic import BaseModel

app = FastAPI()
producer: AIOKafkaProducer | None = None

KAFKA_MOVIES_TOPIC = "movie-events"
KAFKA_USER_TOPIC = "user-events"
KAFKA_PAYMENT_TOPIC = "payment-events"
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BROKERS", "localhost:9092")

@app.on_event("startup")
async def startup_event():
    global producer
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    asyncio.create_task(consume())


@app.on_event("shutdown")
async def shutdown_event():
    if producer:
        await producer.stop()
        

class Event(BaseModel):
    id: str 
    type: str 
    timestamp: datetime
    payload: dict[str, Any]


class EventResponse(BaseModel):
    status: str
    partition: int
    offset: int
    event: Event
    
class MovieEvent(BaseModel):
    movie_id: int 
    title: str 
    action: str 
    user_id: Optional[int] 
    rating: Optional[float] 
    genres: Optional[List[str]] 
    description: Optional[str]
    
class UserEvent(BaseModel):
    user_id: int 
    username: Optional[str] 
    email: Optional[str] 
    action: str 
    timestamp: datetime 


class PaymentEvent(BaseModel):
    payment_id: int 
    user_id: int 
    amount: float 
    status: str 
    timestamp: datetime 
    method_type: Optional[str] 

@app.get("/api/events/health")
async def health():
    return { "status": True }   

@app.post("/api/events/movie", status_code=201)
async def events_movie(event: MovieEvent):
    logging.info(f"Message body: {event.json()}")
    metadata = await producer.send_and_wait(KAFKA_MOVIES_TOPIC, event.json().encode("utf-8"))
    return {
        "status": "success",
        "partition": metadata.partition,
        "offset": metadata.offset,
        "event":event
    }

@app.post("/api/events/user", status_code=201)
async def events_user(event: UserEvent):
    logging.info(f"Message body: {event.json()}")
    metadata = await producer.send_and_wait(KAFKA_USER_TOPIC, event.json().encode("utf-8"))
    return {
        "status": "success",
        "partition": metadata.partition,
        "offset": metadata.offset,
        "event":event
    }
    
@app.post("/api/events/payment", status_code=201)
async def events_payment(event: PaymentEvent):
    logging.info(f"Message body: {event.json()}")
    metadata = await producer.send_and_wait(KAFKA_PAYMENT_TOPIC, event.json().encode("utf-8"))
    return {
        "status": "success",
        "partition": metadata.partition,
        "offset": metadata.offset,
        "event":event
    }
    
async def consume():
    consumer = AIOKafkaConsumer(
        KAFKA_MOVIES_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="movies-group",
        auto_offset_reset="earliest"
    )
    await consumer.start()
    try:
        async for msg in consumer:
            print(f"[Kafka] Received: {msg.value.decode('utf-8')}")
    finally:
        await consumer.stop()         
