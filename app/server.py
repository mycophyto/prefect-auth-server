import os
import time
import logging
from fastapi import Response
from starlette.requests import HTTPConnection
from starlette.responses import PlainTextResponse
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    SimpleUser,
    AuthenticationError,
)
from prefect.server.api.server import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

apikey = "Bearer " + os.environ["PREFECT_API_KEY"]
basic_auth = "Basic " + os.environ["PREFECT_BASIC_AUTH"]


class CustomAuth(AuthenticationBackend):
    async def authenticate(self, conn: HTTPConnection):
        # Allow health check endpoint without authentication
        if conn.url.path == "/api/health":
            return None

        # Allow version check endpoint with authentication
        if conn.url.path == "/api/admin/version":
            if "Authorization" in conn.headers:
                auth = conn.headers["Authorization"]
                if auth == apikey or auth == basic_auth:
                    return AuthCredentials(["auth"]), SimpleUser("admin")
            raise AuthenticationError("invalid token for version check")

        if conn.url.path == "/api/events/in":
            # Check for WebSocket upgrade request
            if conn.headers.get("upgrade", "").lower() == "websocket":
                return AuthCredentials(["auth"]), SimpleUser("websocket")

        if "Authorization" not in conn.headers:
            raise AuthenticationError("no token")

        auth = conn.headers["Authorization"]

        # For API routes (including admin routes), accept both API key and Basic auth
        if conn.url.path.startswith("/api/"):
            if auth == apikey:
                return AuthCredentials(["auth"]), SimpleUser("api")
            elif auth == basic_auth:
                return AuthCredentials(["auth"]), SimpleUser("user")
            raise AuthenticationError(
                "invalid token - API routes require valid API key or basic auth"
            )

        # For non-API routes, only accept basic auth
        if auth == basic_auth:
            return AuthCredentials(["auth"]), SimpleUser("user")

        raise AuthenticationError("invalid token - non-API routes require basic auth")


def handler_error(conn: HTTPConnection, exc: Exception) -> Response:
    return PlainTextResponse(
        "Login required",
        401,
        headers={"WWW-Authenticate": f'Basic realm="Unauthorized: {exc}"'},
    )


def create_auth_app():
    logger.info("Initializing authentication server...")
    start_time = time.time()

    app = create_app()

    @app.get("/api/health")
    async def health_check():
        return {"status": "healthy"}

    app.add_middleware(
        AuthenticationMiddleware,
        backend=CustomAuth(),
        on_error=handler_error,
    )

    @app.on_event("startup")
    async def startup_event():
        logger.info(
            f"Server started successfully in {time.time() - start_time:.2f} seconds"
        )

    return app
