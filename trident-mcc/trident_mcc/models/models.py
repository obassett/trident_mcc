from __future__ import annotations
from datetime import datetime, timedelta
import logging

from typing import Optional
from enum import IntEnum, Enum
from pydantic import BaseModel


logger = logging.getLogger("trident_mcc.healthz")


# Make sure StateEnum and StateMessageEnum are in same sequence, we zip them for lookups.
class StateEnum(IntEnum):
    OK = 200
    STARTING = 503
    ERROR = 500
    TIMEOUT = 504


class StateMessageEnum(str, Enum):
    OK = "OK"
    STARTING = "Starting Up"
    ERROR = "Error"
    TIMEOUT = "Gateway Time-Out - No Updated Status Available"


class StatusUpdate(BaseModel):
    state: StateEnum
    message: Optional[str] = None


class AppHealth(BaseModel):
    state: StateEnum
    message: Optional[str] = None
    last_update: Optional[datetime] = datetime.now()

    async def update_status(self, status_update: StatusUpdate):
        self.state = status_update.state
        self.message = status_update.message
        self.last_update = datetime.now()

    async def validate_status(self, polling_interval: int) -> None:
        """Validates liveness

        Checks the current value of app_state if it is older than interval-time sets the
        state to StateEnum.TIMEOUT

        :param polling_interval
        """
        logger.debug("validate_status is checking app state's last update time")
        if self.last_update > (
            datetime.now() + timedelta(seconds=(polling_interval + 10))
        ):  # Make sure app state is updated at least every Polling interval + 10 seconds (This should be enough time to run)
            logger.warning(
                f"Last Update to state was more than {polling_interval}s ago."
            )
            await self.update_status(StatusUpdate(state=StateEnum.TIMEOUT))
        else:
            logger.debug(f"app_state last update was within a polling period.")
