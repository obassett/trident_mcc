from starlette.applications import Starlette
from starlette.responses import Response, HTMLResponse
from starlette.routing import Route

from enum import Enum


class AppState(Enum):
    OK = 200
    STARTING = 100
    ERROR = 500


async def healthz(request):
    """Kubernetees Health Check"""
    logging.debug(f"Received health check request - current state: {app.state.HEALTH}")
    if (
        app.state.HEALTH_LAST_UPDATE
        + timedelta(seconds=(app.state.POLLING_INTERVAL + 10))
        < datetime.now()
    ):  # Make sure app state is updated at least every Polling interval + 10 seconds (This should be enough time to run)
        logging.debug(
            f"Received health check request - Last Update: {app.state.HEALTH_LAST_UPDATE} "
        )
        response = Response(content="ERROR", status_code=500)
    elif app.state.HEALTH == AppState.OK:  # We are healthy Return OK
        response = Response(content="OK", status_code=200)
    elif app.state.HEALTH == AppState.STARTING:  # We are still starting.
        response = Response(content="Starting Up", status_code=202)
    else:  # If nothing else matches then return not okay.
        response = Response(content="ERROR", status_code=500)

    return response


async def startup():
    """Startup Tasks"""
    logger.info("Application Starting Up")
    # Set Health State
    app.state.HEALTH = AppState.STARTING
    app.state.HEALTH_LAST_UPDATE = datetime.now()
    app.state.POLLING_INTERVAL = POLLING_INTERVAL


# Define HTTP Routes
routes = [Route("/healthz", healthz)]

#
app = Starlette(debug=app_debug, routes=routes, on_startup=[startup])