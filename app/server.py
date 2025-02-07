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

        if "Authorization" not in conn.headers:
            raise AuthenticationError("no token")

        auth = conn.headers["Authorization"]

        # For API routes, only accept API key authentication
        if conn.url.path.startswith("/api/"):
            if auth == apikey:
                return AuthCredentials(["auth"]), SimpleUser("api")
            raise AuthenticationError("invalid token - API routes require API key")

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
    app = create_app()
    app.add_middleware(
        AuthenticationMiddleware,
        backend=CustomAuth(),
        on_error=handler_error,
    )
    return app
