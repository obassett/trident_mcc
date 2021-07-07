from email import message
import signal
import sys
import os
import logging

from datetime import datetime, timedelta
import time
from fastapi import responses

import requests
from requests.exceptions import ConnectionError

import json
import trident_mcc.k8s_client as k8s_client
import trident_mcc.netapp_client as na_client
from trident_mcc.models import StateEnum, StatusUpdate

# What do we want to configure
# ---------------------------
"""
Debug Logging
Polling Interval = Default 300 (5 mins)
Trident Namespace = Default trident - potentially auto-detect, but better to restrict

"""
# TODO: Validation of environment options
DEBUG = os.getenv("DEBUG", None)
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", 300))
TRIDENT_NAMESPACE = os.getenv("TRIDENT_NAMESPACE", "trident")
KUBE_CONFIG_LOCATION = os.getenv("KUBE_CONFIG_LOCATION", None)


###
# Initialise logging
###
# Check Debug environment variable to configure logging level
if DEBUG:
    loggerlevel = logging.DEBUG
    app_debug = True
else:
    loggerlevel = logging.INFO
    app_debug = False

# Create Logger with Applicaiton Name
logger = logging.getLogger("trident_mcc")
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
###


# Initialise K8s Client
if KUBE_CONFIG_LOCATION:
    k8sclient = k8s_client.K8sclient(
        kube_config=KUBE_CONFIG_LOCATION,
        trident_namespace=TRIDENT_NAMESPACE,
    )
else:
    k8sclient = k8s_client.K8sclient(
        trident_namespace=TRIDENT_NAMESPACE,
    )


# Interupt Handler - To cleaning exits loops, could take up to POLLING_INTERVAL to exit
class SignalCatcher:
    terminate = False
    in_progress = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_cleanly)
        signal.signal(signal.SIGTERM, self.exit_cleanly)

    def start_job(self):
        self._start_time = time.time()
        logger.debug("Starting Interation")
        self.in_progress = True

    def end_job(self):
        self._end_time = time.time()
        logger.debug(
            f"Ending Iteration - duration: '{self._end_time - self._start_time:.2f}s'"
        )
        self.in_progress = False

    def exit_cleanly(self, *args):
        logger.info(f"Received termination signal- Terminating Cleanly")
        if self.in_progress:
            self.terminate = True
        else:
            sys.exit()


def update_healthcheck(status_update: StatusUpdate):
    """Updates Healthcheck API

    Does HTTP Post to the healthcheck backend with a StatusUpdate Message

    :param status_update: StatusUpdate State and Message to set the healthcheck to
    :type status_update: trident_mcc.models.StatusUpdate
    """
    logger.debug("update_healthcheck starting.")
    start_time = time.time()
    APIURL = "http://localhost:8000/update_status"
    headers = {"Content-Type": "application/json"}

    if not isinstance(status_update, StatusUpdate):
        raise TypeError(
            f"Expected status_update to be of type 'trident_mcc.models.StatusUpdate' not '{type(status_update)}'"
        )

    try:
        response = requests.post(url=APIURL, data=status_update.json(), headers=headers)
    except ConnectionError as err:
        logger.error(
            f"Unable to connect to Healthcheck Service - Make sure it is running"
        )
    else:
        if response.status_code == 200:
            logger.debug(f"Successfully updated status with healthcheck service")
        else:
            logger.error(
                f"Update to Healthcheck Service failed with status_code {response.status_code}"
            )

    end_time = time.time()
    logger.debug(f"update_healthcheck finished in {end_time - start_time:.2f}s")


def check_backends():
    # Get all the backends
    has_error = False
    all_backends_count = 0
    managed_backend_count = 0
    patch_count = 0

    trident_backends = k8sclient.get_trident_backends()
    if not trident_backends:
        status_message = f"No Backends found"
        logger.info(status_message)
        update_healthcheck(
            StatusUpdate(
                state=StateEnum.OK,
                message=status_message,
            )
        )
        return

    for trident_config in trident_backends:
        be_name = trident_config.metadata.name
        logger.debug(f"Processing TridentBackendConfig - '{be_name}'")
        # For Each Backend
        # 1. If it is  ONTAP it might be metro do stuff - otherwise ignore non-metro backends (maybe inverse with break)
        all_backends_count += 1
        if not "ontap" in trident_config.spec.storageDriverName:
            logger.debug(
                f"TridentBackendConfig '{be_name}' not an ONTAP backend. It is '{trident_config.spec.storageDriverName}'"
            )
            continue

        managed_backend_count += 1
        # Is this already managed by us, e.g. have we already update the UUID in annotations
        existing_svm_name = trident_config.spec.get("svm", None)
        existing_svm_uuid = trident_config.metadata.annotations.get(
            "trident_mcc_svm_uuid", None
        )

        # Initialize NetApp Backend - Using credentials pulled from the k8s api
        netapp_client = na_client.NetAppClient(
            **k8sclient.get_na_connection_properties(trident_config)
        )

        svm_details = {}
        if existing_svm_uuid is not None:
            # get by UUID
            svm_details = netapp_client.get_svm_by_uuid(existing_svm_uuid)
        elif existing_svm_name is not None:
            # get by SVM Name
            svm_details = netapp_client.get_svm_by_name(existing_svm_name)
        else:
            # Assume it is an SVM scoped management Lif and we will only be able to retrieve a single svm
            svm_details = netapp_client.get_svm()

        if not svm_details:
            logger.error(
                f"Unable to match get SVM Details for backend {be_name}- Please check configuration"
            )
            continue

        if (
            svm_details["uuid"] == existing_svm_uuid
            and svm_details["name"] == existing_svm_name
        ):
            logger.info(
                f"SVM Details for TridentBackendConfig '{be_name}' - SVM Name '{existing_svm_name}' - UUID '{existing_svm_uuid}' have not changed"
            )
            continue
        else:
            patch_result = k8sclient._patch_backend_with_svmname(
                trident_config,
                svm_name=svm_details["name"],
                svm_uuid=svm_details["uuid"],
            )
            if patch_result:
                patch_count += 1
    else:
        # Sucessfully Processed all backends report success
        status_message = f"Successfully Checked Backends - ONTAP Backends being monitored: {managed_backend_count}/{all_backends_count} - Patched: {patch_count}/{managed_backend_count} backends"
        logger.info(status_message)
        update_healthcheck(
            StatusUpdate(
                state=StateEnum.OK,
                message=status_message,
            )
        )


def main():

    # Intialise Handler
    job_monitor = SignalCatcher()
    while not job_monitor.terminate:
        job_monitor.start_job()
        try:
            check_backends()
        finally:
            # Clean Up
            pass
        job_monitor.end_job()
        # Check to see if we got termination during run, before sleeping
        if job_monitor.terminate:
            logger.info("Terminating")
            break
        logger.debug(f"Sleeping for {POLLING_INTERVAL}s")
        time.sleep(POLLING_INTERVAL)


if __name__ == "__main__":
    main()