from typing import ItemsView
from .models import StatusUpdate, StateEnum, AppHealth, StateMessageEnum


def lookup_status_message(status_code: StateEnum) -> StateMessageEnum:

    # Static Mapping of StateEnum to StateMessageEnum
    for code, message in zip(StateEnum, StateMessageEnum):
        if code == status_code:
            return message
    else:
        return None
