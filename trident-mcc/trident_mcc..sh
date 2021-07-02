#! /bin/bash

poetry run uvicorn healthz:app --log-config logging.yaml &
poetry run python3 -m trident_mcc
