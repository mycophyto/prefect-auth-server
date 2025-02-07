import os
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
        if conn.url.path == "/api/health":
            return None

        logger.debug(f"Received request path: {conn.url.path}")

        if "Authorization" not in conn.headers:
            logger.debug("No Authorization header found")
            raise AuthenticationError("no token")

        auth = conn.headers["Authorization"]
        logger.debug(f"Received Authorization header: {auth}")
        logger.debug(f"Expected basic_auth value: {basic_auth}")

        if auth == apikey:
            logger.debug("API key authentication successful")
            return AuthCredentials(["auth"]), SimpleUser("api")

        if auth == basic_auth:
            logger.debug("Basic auth authentication successful")
            return AuthCredentials(["auth"]), SimpleUser("user")

        logger.debug("Authentication failed - invalid token")
        raise AuthenticationError("invalid token")


def handler_error(conn: HTTPConnection, exc: Exception) -> Response:
    return PlainTextResponse(
        "Login required",
        401,
        headers={"WWW-Authenticate": f'Basic realm="Unauthorized: {exc}"'},
    )


def create_auth_app():
    app = create_app()
    app.add_middleware(
        AuthenticationMiddleware,
        backend=CustomAuth(),
        on_error=handler_error,
    )
    return app
