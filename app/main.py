import os
import json
import socket
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
import asyncpg

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

CACHE_TTL = 300  # 5 minutes de cache

# Global variables
pool = None
r = None
db_semaphore = None       # Limits concurrent DB queries
inflight_locks = {}       # Prevents cache stampede (one DB query per key)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool, r, db_semaphore
    # Startup
    pool = await asyncpg.create_pool(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        min_size=30,
        max_size=30
    )
    redis_pool = ConnectionPool(
        host=REDIS_HOST,
        port=6379,
        decode_responses=True,
        max_connections=500
    )
    r = redis.Redis(connection_pool=redis_pool)
    db_semaphore = asyncio.Semaphore(25)  # Max 25 concurrent DB queries per worker
    print(f"[READY] {socket.gethostname()} — pool: 30 conns, semaphore: 25")
    yield
    # Shutdown
    await pool.close()
    await r.close()

app = FastAPI(lifespan=lifespan)


async def fetch_person_from_db(ranking: int) -> dict:
    """
    Single-flight pattern: if 500 requests ask for ranking=42 at the same time,
    only ONE hits the database. The 499 others wait for that result.
    """
    cache_key = f"person:ranking:{ranking}"

    # Check if another coroutine is already fetching this exact key
    if cache_key in inflight_locks:
        # Wait for the other coroutine to finish, then read from cache
        await inflight_locks[cache_key].wait()
        cached = await r.get(cache_key)
        if cached:
            return json.loads(cached)

    # This coroutine is the "leader" for this key
    event = asyncio.Event()
    inflight_locks[cache_key] = event

    try:
        # Semaphore limits total concurrent DB queries to avoid pool exhaustion
        async with db_semaphore:
            async with pool.acquire(timeout=15) as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM pantheon WHERE ranking = $1", ranking
                )
                if row is None:
                    return None

                person_data = dict(row)

                # Cache the result
                try:
                    await r.setex(
                        cache_key, CACHE_TTL,
                        json.dumps(person_data, default=str)
                    )
                except Exception:
                    pass

                return person_data
    finally:
        # Wake up all waiting coroutines and clean up
        event.set()
        inflight_locks.pop(cache_key, None)


@app.get("/")
async def read_root():
    return {"message": f"Hello from API instance: {socket.gethostname()}"}


@app.get("/people/{ranking}")
async def read_person(ranking: int):
    cache_key = f"person:ranking:{ranking}"

    # 1. Check Redis cache
    try:
        cached_data = await r.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
    except Exception:
        pass

    # 2. Fetch from DB with single-flight + semaphore + retry
    last_error = None
    for attempt in range(3):
        try:
            person_data = await fetch_person_from_db(ranking)

            if person_data is None:
                raise HTTPException(status_code=404, detail="Person not found")

            person_data["_source"] = f"Database (served by {socket.gethostname()})"
            return person_data

        except HTTPException:
            raise
        except Exception as e:
            last_error = e
            await asyncio.sleep(0.05 * (attempt + 1))

    raise HTTPException(status_code=500, detail=str(last_error))


@app.get("/people")
async def read_people(limit: int = 10):
    try:
        async with db_semaphore:
            async with pool.acquire(timeout=15) as conn:
                rows = await conn.fetch(
                    "SELECT * FROM pantheon ORDER BY ranking LIMIT $1", limit
                )
                people = [dict(row) for row in rows]
                return {"count": len(people), "data": people, "server": socket.gethostname()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
