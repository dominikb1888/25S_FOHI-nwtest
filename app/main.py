from fastapi import FastAPI
import redis

app = FastAPI()

# Connect to Redis
r = redis.Redis(host="redis", port=6379, decode_responses=True)

@app.get("/")
def read_root():
    # Example: increment a counter in Redis
    count = r.incr("counter")
    return {"Hello": "World", "counter": count}

