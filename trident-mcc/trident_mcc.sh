#! /bin/bash

poetry run uvicorn trident_mcc.healthz:app --log-config trident_mcc/logging.yaml &
poetry run python3 -m trident_mcc
