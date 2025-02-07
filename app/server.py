import os
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

apikey = "Bearer " + os.environ["PREFECT_API_KEY"]
basic_auth = "Basic " + os.environ["PREFECT_BASIC_AUTH"]


class CustomAuth(AuthenticationBackend):
    async def authenticate(self, conn: HTTPConnection):
        if conn.url.path == "/api/health":
            return None

        if "Authorization" not in conn.headers:
            raise AuthenticationError("no token")

        auth = conn.headers["Authorization"]

        if auth == apikey:
            return AuthCredentials(["auth"]), SimpleUser("api")

        if auth == basic_auth:
            return AuthCredentials(["auth"]), SimpleUser("user")

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
