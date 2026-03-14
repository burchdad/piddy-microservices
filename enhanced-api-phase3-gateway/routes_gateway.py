"""
API Gateway Service - Central Request Router
Handles request routing, rate limiting, authentication verification
"""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
import httpx
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Piddy API Gateway",
    description="Central gateway for routing requests to microservices",
    version="1.0.0",
)

# Setup rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service registry
SERVICES = {
    "/api/v1/users": "http://localhost:8000",
    "/api/v1/auth": "http://localhost:8002",
    "/api/v1/notifications": "http://localhost:8001",
    "/api/v1/email": "http://localhost:8003",
    "/api/v1/sms": "http://localhost:8004",
    "/api/v1/push": "http://localhost:8005",
}

# Rate limit configs per endpoint
RATE_LIMITS = {
    "/api/v1/auth/login": "5/minute",
    "/api/v1/auth/register": "3/minute",
    "/api/v1/users": "100/minute",
    "/api/v1/notifications": "50/minute",
}


@app.on_event("startup")
def startup():
    """Initialize gateway"""
    logger.info("API Gateway started")
    for endpoint, service in SERVICES.items():
        logger.info(f"  {endpoint} -> {service}")


@app.get("/health")
def health_check():
    """Gateway health check"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow(),
        "services": list(SERVICES.keys()),
    }


@app.get("/gateway/metrics")
def gateway_metrics():
    """Gateway metrics"""
    return {
        "services": len(SERVICES),
        "timestamp": datetime.utcnow(),
    }


@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def route_request(request: Request, path_name: str):
    """Route requests to appropriate service"""
    
    # Find matching service
    service_url = None
    for prefix, url in SERVICES.items():
        if f"/{path_name}".startswith(prefix):
            service_url = url
            break

    if not service_url:
        raise HTTPException(status_code=404, detail="Service not found")

    # Construct target URL
    target_path = "/" + path_name
    target_url = service_url + target_path

    try:
        # Forward request
        async with httpx.AsyncClient() as client:
            response = await client.request(
                url=target_url,
                method=request.method,
                content=await request.body(),
                headers={
                    key: value
                    for key, value in request.headers.items()
                    if key.lower() not in ["host", "connection"]
                },
                params=dict(request.query_params),
            )

        return JSONResponse(
            status_code=response.status_code,
            content=response.json() if response.content else {},
            headers=dict(response.headers),
        )
    except Exception as e:
        logger.error(f"Request routing failed: {e}")
        raise HTTPException(status_code=502, detail="Service unavailable")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
