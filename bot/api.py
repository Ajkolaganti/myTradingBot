from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import API_HOST, API_PORT
from .shared import LOG_BUFFER, SNAPSHOTS

app = FastAPI(title="Trading Bot API", version="1.0.0")

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/logs")
def logs(limit: int = 200):
    return {"logs": LOG_BUFFER.latest(limit=limit)}


@app.get("/snapshot")
def snapshot():
    return SNAPSHOTS.get()


@app.get("/status")
def status():
    return SNAPSHOTS.get().get("status", {})


@app.get("/metrics")
def metrics():
    return SNAPSHOTS.get().get("metrics", {})


@app.get("/positions")
def positions():
    return SNAPSHOTS.get().get("positions", [])


@app.get("/candidates")
def candidates():
    return SNAPSHOTS.get().get("candidates", [])


def run_api():
    import uvicorn

    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")

