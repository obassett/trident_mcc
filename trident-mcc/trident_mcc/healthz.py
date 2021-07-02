from __future__ import annotations
from email import message
import os
import logging
from typing import Optional

from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from enum import Enum, IntEnum


from trident_mcc.models import (
    AppHealth,
    StateEnum,
    StatusUpdate,
    StateMessageEnum,
    lookup_status_message,
)


app = FastAPI()

# Environment Variables -
DEBUG = os.getenv("DEBUG", None)
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", 300))

# Set Up Logging
if DEBUG:
    loggerlevel = logging.DEBUG
    app_debug = True
    logging.getLogger("uvicorn.error").setLevel(loggerlevel)
    logging.getLogger("uvicorn.access").setLevel(loggerlevel)
else:
    loggerlevel = logging.INFO
    app_debug = False

# Create Logger with Applicaiton Name
logger = logging.getLogger("trident_mcc.healthz")
# Set Level based on DEBUG environment Variable
logger.setLevel(loggerlevel)
ch = logging.StreamHandler()  # Std Err Logging
# Format Log Output - 2021-01-23 00:00:00:trident_mcc.module:INFO - Message
log_formatter = logging.Formatter(
    "%(asctime)s:%(name)s.%(module)s:%(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
ch.setFormatter(log_formatter)
logger.addHandler(ch)


@app.get("/healthz")
async def healthz():
    """Kubernetees Health Check"""
    logger.debug(f"Received health check request - current state: {app_state.state} ")
    await app_state.validate_status(POLLING_INTERVAL)

    lookup_status_message(app_state.state)
    if app_state.message:
        response_content = " - ".join(
            [lookup_status_message(app_state.state), app_state.message]
        )
    else:
        response_content = lookup_status_message(app_state.state)

    response = PlainTextResponse(status_code=app_state.state, content=response_content)

    return response


@app.post("/update_status")
async def update_status(status_update: StatusUpdate):
    """Updates the application status with state and timestamp

    This is called via the /update_status endpoint with a POST operation.
    """
    logger.debug(
        f"/update_status - Received Application Status Update - {status_update} "
    )
    await app_state.update_status(status_update)

    if app_state.state == status_update.state:
        logger.info(f"/update_status - Successfully Updated status")
        return PlainTextResponse(content="OK", status_code=200)
    else:
        logger.warning(f"/update_status - Unable to set status")
        return PlainTextResponse(content="FAILED", status_code=500)


@app.on_event("startup")
async def startup():
    """Startup Tasks"""
    logger.info("Healthcheck Application Starting Up")
    # Initialize State
    global app_state
    app_state = AppHealth(
        state=StateEnum.STARTING, message="Application Starting - No Updates Recieved"
    )
