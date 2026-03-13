import os
import json
import socket
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import redis.asyncio as redis
import asyncpg

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

# Global variables for connection pool and redis client
pool = None
r = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool, r
    # Startup
    pool = await asyncpg.create_pool(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        min_size=10,
        max_size=50
    )
    r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
    yield
    # Shutdown
    await pool.close()
    await r.close()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_root():
    return {"message": f"Hello from API instance: {socket.gethostname()}"}

@app.get("/people/{ranking}")
async def read_person(ranking: int):
    cache_key = f"person:ranking:{ranking}"
    cached_data = await r.get(cache_key)
    
    if cached_data:
        print(f"Cache HIT for ranking {ranking}")
        return json.loads(cached_data)
    
    print(f"Cache MISS for ranking {ranking}")
    
    # 2. Query Database using async pool
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM pantheon WHERE ranking = $1", ranking)
            
            if row is None:
                raise HTTPException(status_code=404, detail="Person not found")
            
            person_data = dict(row)
            
            # 3. Save to Redis (expire in 60 seconds)
            await r.setex(cache_key, 60, json.dumps(person_data, default=str))
            
            # Add metadata about source
            person_data["_source"] = f"Database (served by {socket.gethostname()})"
            return person_data
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/people")
async def read_people(limit: int = 10):
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM pantheon ORDER BY ranking LIMIT $1", limit)
            people = [dict(row) for row in rows]
            return {"count": len(people), "data": people, "server": socket.gethostname()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
