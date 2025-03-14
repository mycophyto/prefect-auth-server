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

# Enhanced logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,  # This forces the configuration even if logging was already configured
)
logger = logging.getLogger(__name__)
# Ensure the logger level is set to DEBUG
logger.setLevel(logging.DEBUG)

# Add a stream handler if needed
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)

apikey = "Bearer " + os.environ["PREFECT_API_KEY"]
basic_auth = "Basic " + os.environ["PREFECT_BASIC_AUTH"]


class CustomAuth(AuthenticationBackend):
    async def authenticate(self, conn: HTTPConnection):
        logger.info(f"Health Check - Received request path: {conn.url.path}")

        if conn.url.path == "/api/health":
            logger.info("Health check endpoint accessed")
            return None

        if "Authorization" not in conn.headers:
            logger.debug("No Authorization header found")
            raise AuthenticationError("no token")

        auth = conn.headers["Authorization"]
        logger.debug(f"Received Authorization header: {auth}")

        # For API routes, accept both API key and Basic auth
        if conn.url.path.startswith("/api/"):
            logger.debug("API route detected - checking authentication")
            if auth == apikey:
                logger.debug("API key authentication successful")
                return AuthCredentials(["auth"]), SimpleUser("api")
            elif auth == basic_auth:
                logger.debug("Basic auth authentication successful for API route")
                return AuthCredentials(["auth"]), SimpleUser("user")
            logger.debug("Authentication failed for API route")
            raise AuthenticationError(
                "invalid token - API routes require valid API key or basic auth"
            )

        # For non-API routes, only accept basic auth
        logger.debug("Non-API route detected - checking basic auth")
        if auth == basic_auth:
            logger.debug("Basic auth authentication successful")
            return AuthCredentials(["auth"]), SimpleUser("user")

        logger.debug("Basic auth authentication failed")
        raise AuthenticationError("invalid token - non-API routes require basic auth")


def handler_error(conn: HTTPConnection, exc: Exception) -> Response:
    return PlainTextResponse(
        "Login required",
        401,
        headers={"WWW-Authenticate": f'Basic realm="Unauthorized: {exc}"'},
    )


def create_auth_app():
    logger.info("Starting app creation...")
    start_time = time.time()

    app = create_app()

    @app.get("/api/health")
    async def health_check():
        logger.info("Health check endpoint called")
        return {"status": "healthy"}

    logger.info(f"Base app created in {time.time() - start_time:.2f} seconds")

    middleware_start = time.time()
    app.add_middleware(
        AuthenticationMiddleware,
        backend=CustomAuth(),
        on_error=handler_error,
    )
    logger.info(
        f"Auth middleware added in {time.time() - middleware_start:.2f} seconds"
    )

    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting server initialization...")
        startup_start = time.time()
        # This will help identify if any Prefect-specific initialization is slow
        logger.info(
            f"Server initialization complete in {time.time() - startup_start:.2f} seconds"
        )
        logger.info(f"Total startup time: {time.time() - start_time:.2f} seconds")

    return app
