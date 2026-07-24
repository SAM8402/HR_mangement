"""Application entry point.

Launches the FastAPI application server using Uvicorn with hot-reload
enabled for local development.
"""

import logging

import uvicorn

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting HR Management Backend on http://127.0.0.1:8000")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
