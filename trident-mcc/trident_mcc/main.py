import os
import logging

import json
import trident_mcc.k8s_client as k8s_client
import trident_mcc.netapp_client as na_client

# What do we want to configure
# ---------------------------
"""
Debug Logging
Polling Interval = Default 300 (5 mins)
Trident Namespace = Default trident - potentially auto-detect, but better to restrict

"""
# TODO: Validation of environment options
DEBUG = os.getenv("DEBUG", None)
POLLING_INTERVAL = os.getenv("POLL_INT", 300)
TRIDENT_NAMESPACE = os.getenv("TRIDENT_NAMESPACE", "trident")

# Initialise logging

# Check Debug environment variable to configure logging level
if DEBUG:
    loggerlevel = logging.DEBUG
else:
    loggerlevel = logging.INFO

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


# Initialise K8s Client
k8sclient = k8s_client.K8sclient(
    kube_config="trident-mcc/trident_mcc/temp/kube.config",
    trident_namespace="trident",
)


def check_backends():
    # Get all the Trident Backends
    # For Each Backend Get the details for the NetApp API:
    #   1. Management Lif Ip Address
    #   2. Credentials (username/pasword, client certificate?)
    #   3. SVM Name and UUID from Backend Configuration
    #
    # Connect to NetApp Rest API - Get details for SVM to validate - name, uuid, state, subtype (this will tell us if it is MCC)
    # If it is not MCC ignore
    # If it is MCC and SVM Name is not set in the config, or it is incorrect in the config, and the UUID matches -
    #   - Update the SVM name in the backend config
    #   - Annotate the config with a counter for config updates
    #   - Annotate the config to say we are tracking it.

    # 1. Get List of Backends

    pass


def main():
    # Perform Validation (this will be changed into a job that runs in a loop)
    for item in k8sclient._get_trident_backends():
        print(f"name: {item.metadata.name}")
        print(f"Backend name: {item.status.backendInfo.backendName}")
        print(f"Backend UUID: {item.status.backendInfo.backendUUID}")
        print(f"Management LIF: {item.spec.managementLIF}")
        print(f"storageDriverName: {item.spec.storageDriverName}")

        # Need to extract Credentials - Options could be Secret
        response = k8sclient._get_backend_secret(item)
        secrets = k8sclient._decode_secrets(response)

        svm_details = na_client.get_svm_details(
            svm_uuid=item.status.backendInfo.backendUUID,
            management_lif=item.spec.managementLIF,
            **secrets,
        )
        print("----------------------------------------")
        print(svm_details)

        # TODO : Need to work out better comparison method, svm uuid isn';t returned by trident to compare.
        #
        # Thinking : On first run - annotate the TridentBackendConfig with the svm_uuid and use this is ensure
        # we are talking to the same SVM.

        # print(secrets)
        # print(type(response))
        # print(f"encoded_username = {response.data.username}")
        # print(f"encoded_password = {response.data.password}")

        # if item.metadata.name == "test-ontap-nas":
        #     # print(item.to_dict())
        #     results = k8sclient._patch_backend_with_svmname(item, "k8s_01")
        #     # print(results)
        pass
        # print(type(item))
        # print(dir(item))
        # print(item)
        # item_object = k8sclient._get_trident_backend_by_name(item.metadata.name)
        # print(type(item_object))
        # print(dir(item_object))
        # print(item_object)


if __name__ == "__main__":
    main()
