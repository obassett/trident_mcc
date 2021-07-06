#! /bin/bash

poetry run uvicorn trident_mcc.healthz:app --host 0.0.0.0 --log-config trident_mcc/logging.yaml &
poetry run python3 -m trident_mcc
