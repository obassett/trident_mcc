from __future__ import annotations
import logging
from pathlib import Path
from typing import List
import time

import base64

from kubernetes import config as k8sconfig, dynamic
from kubernetes.config import ConfigException
from kubernetes.client import api_client
from kubernetes.dynamic.exceptions import (
    NotFoundError,
    ResourceNotFoundError,
    ApiException,
)
from kubernetes.dynamic.resource import ResourceField, ResourceInstance


logger = logging.getLogger("trident_mcc.k8s_client")


class K8sclient:
    def __init__(
        self, kube_config: str = None, trident_namespace: str = "trident"
    ) -> None:
        """Custom K8sclient class to allow for simplifing trident access

        Acts a a datastore for kubeconfig and handles dynamic client configuraiton for
        require Trident Backend Configuration API.

        :param kube_config: The location to a kube_config file. Current set context will be used. If not specified will default to in-cluster kube_config
            (default is None)
        :type kube_config: str
        :param trident_namespace: The kubernetes namespace for trident objects.
            (default is 'trident')
        :type trident_namespace: str
        :returns: None
        :rtype: None
        :raises TypeError: On invalid parameter types.
        :raises ValueError: On invalid parameter values (file doesn't exist, namespace doesn't exist)

        """
        if not kube_config:
            logger.info("Using in cluster kubernetes configuration")
            try:
                self._kube_config = k8sconfig.load_incluster_config()
            except ConfigException as err:
                logger.error(
                    f"Unable to load in-cluster configuration - expected to be running inside a pod"
                )
                raise ConfigException(
                    f"Unable to load in-cluster configuration - expected to be running inside a pod"
                )
        elif isinstance(kube_config, str):
            # Make sure that file exists
            if Path(kube_config).is_file() and Path(kube_config).exists():
                # Try to load kube_config
                try:
                    self._kube_config = k8sconfig.load_kube_config(
                        config_file=kube_config
                    )
                except ConfigException as err:
                    logger.error(
                        f"Unable to load specified kube_config: {kube_config=}"
                    )
                    raise err
            else:
                raise ValueError(
                    f"The specified 'kube_config' file ({kube_config}) does not exist or isn't a file."
                )
        else:
            raise TypeError(
                f"The specified 'kube_config' is of type {type(kube_config)} not str"
            )

        # Create Dynamic k8s client
        try:
            self.client = dynamic.DynamicClient(
                api_client.ApiClient(configuration=self._kube_config)
            )
        except Exception as err:
            logger.error(f"Unable to create client - please check configuration")
            raise err

        # Make sure namespace is at least a str)
        if isinstance(trident_namespace, str):
            if self._namespace_exists(trident_namespace):
                self._trident_namespace = trident_namespace
            else:
                raise ValueError(
                    f"The specified trident_namespace ({trident_namespace}) does not exist."
                )
        else:
            raise TypeError(
                f"The specified 'trident_namespace' is of type {type(trident_namespace)} not str"
            )

    def _namespace_exists(self, namespace: str) -> bool:
        """Queries Kubernetes Cluster to make sure specified Namespace exists

        :param namespace: Value to check to ensure it is a valid kubernetes namespace that exists
        :type namespace: str
        :returns: True if namespace exists, False if it doesn't exist
        :rtype: bool
        """
        logger.debug(f"Querying API for namespace '{namespace}'.")
        # Create Namespace Query
        try:
            namespace_api = self.client.resources.get(
                api_version="v1", kind="Namespace"
            )
        except Exception as err:
            logger.error("Unable to access k8s api to get namespaces")
            raise err

        # Check Namespace
        try:
            result = namespace_api.get(name=namespace)
            if result:
                logger.info(f"Sucessfully found namespace '{namespace}'")
                return True
        except ApiException as err:
            logger.critical(
                f"Access to API Forbidden, if using in-cluster config check service-account permissions"
            )
            raise err
        except NotFoundError as err:
            logger.warning(f"Namespace '{namespace}' was not found")
            return False

    def get_trident_backends(self) -> List[ResourceInstance] | None:
        """Queries K8s API and returns a list of all Trident Backend Configurations

        Retrieves TridentBackendConfiguration Objects from K8s API in the Trident Namespace

        :returns: List of TridentBackendConfiguration Objects or None if there aren't any
        :rtype: List[kubernetes.dynamic.resource.ResourceInstance] | None

        """
        start_time = time.time()
        # Get my trident backend api
        logger.debug("Setting up to query trident backends from API Server")
        try:
            trident_backend_api = self.client.resources.get(
                api_version="trident.netapp.io/v1", kind="TridentBackendConfig"
            )
        except ResourceNotFoundError as err:
            logger.error(
                "Unable to find trident CustomResource - Please ensure Trident is installed in Operator Mode"
            )
            raise err

        # Query API and Get Backends.
        logger.debug("Attempting to get all the TridentBackendConfigurations")
        try:
            backend_response = trident_backend_api.get(
                namespace=self._trident_namespace
            )
        except Exception as err:
            raise err

        result = []

        # Return the List if there is at least one backend, otherwise return None
        if len(backend_response.items) > 0:
            logger.info(
                f"Successfully found {len(backend_response.items)} TridentBackendConfig objects in the '{self._trident_namespace}' namespace"
            )
            for backend in backend_response.items:
                result.append(self._get_trident_backend_by_name(backend.metadata.name))
        else:
            logger.warning(
                f"No TridentBackendConfigurations found in '{self._trident_namespace}' namespace."
            )

        end_time = time.time()
        logger.debug(
            f"get_trident_backends execution took {end_time - start_time:.2f}s"
        )
        return result if len(result) > 0 else None

    def _get_trident_backend_by_name(self, backend_name: str) -> ResourceInstance:
        """Queries K8s API and returns the backend as an object for specified Trident Backend Configurations

        Retrieve specified TridentBackendConfiguration Object from K8s API in the Trident Namespace

        :returns: List of TridentBackendConfiguration Objects or None if there aren't any
        :rtype: List[kubernetes.dynamic.resource.ResourceInstance] | None

        """
        logger.debug("Setting up to query trident backend from API Server")
        # Get my trident backend api
        try:
            trident_backend_api = self.client.resources.get(
                api_version="trident.netapp.io/v1", kind="TridentBackendConfig"
            )
        except ResourceNotFoundError as err:
            logger.error(
                "Unable to find trident CustomResource - Please ensure Trident is installed in Operator Mode"
            )
            raise err

        # Query API and Get Backend.
        logger.debug(f"Attempting to get TridentBackendConfig named '{backend_name}'")
        try:
            backend_response = trident_backend_api.get(
                name=backend_name, namespace=self._trident_namespace
            )
        except Exception as err:
            raise err

        return backend_response

    def _get_backend_secret(
        self, trident_backend_config: ResourceInstance
    ) -> ResourceInstance:
        """Queries K8s API and returns the secrets for the specified backend

        :param trident_backend_config: Trident Backend Configuration Retrieved from the Trident Api.
        :returns: Secret Object for the specified backend.
        :rtype: kubernetes.dynamic.resource.ResourceInstance
        """
        logger.debug("Setting up to query secrets from API Server")
        # Get my secret api
        try:
            secrets_api = self.client.resources.get(api_version="v1", kind="Secret")
        except ResourceNotFoundError as err:
            logger.error(
                "Unable to access Secrets Backend - Please verify secret configuration"
            )
            raise err

        # Query API and Get Secret.
        secret_name = trident_backend_config.spec.credentials.name
        logger.debug("Trying to retrieve secret '{secret_name}' from Kubernetes API")
        try:
            backend_response = secrets_api.get(
                name=secret_name,
                namespace=self._trident_namespace,
            )
        except Exception as err:
            logger.error(f"Unable to retrieve secret '{secret_name}'.")
            raise err
        logger.debug(f"Successfully retrieved secret '{secret_name}'.")
        return backend_response

    def _decode_secrets(self, secret: ResourceInstance) -> dict:
        """Decodes secret data from Kubernetes secret ResourceInstance and returns dict

        :param secret: Kubernetes secret ResourceInstance
        :type secret: kubernetes.dynamic.resource.ResourceInstance
        :returns: Python dictionary containing the decoded KV pairs from the secret

        """
        result = {}

        logger.debug(f"Attempting to decode secrets in '{secret.metadata.name}'")
        if len(secret.data.keys()) > 0:
            for k, v in secret.data:
                result[k] = base64.b64decode(v).decode()
        else:
            raise ValueError("")

        if len(result) > 0:
            logger.debug("Successfully decoded secrets")

        return result

    def _patch_backend_with_svmname(
        self, trident_backend: ResourceInstance, svm_name: str, svm_uuid: str
    ) -> bool:
        """Takes the specified trident_backend and svm_name and patches the object.

        Updated the SVM Name in the TridentBackendConfig, and adds/update annotation to let you know
        it has done it, and how many times.

        :param trident_backend: TridentBackendConfig ResourceInstance object you want to patch
        :type trident_backend: kubernetes.dynamic.resource.ResourceInstance
        :param svm_name: Updated svm_name that you want to patch into the object.
        :type svm_name: str
        :return: True or False depending on success updating the backend.
        :rtype: bool

        """
        start_time = time.time()
        logger.debug("Setting up to patch trident backend from API Server")
        # Get my trident backend api
        try:
            trident_backend_api = self.client.resources.get(
                api_version="trident.netapp.io/v1", kind="TridentBackendConfig"
            )
        except ResourceNotFoundError as err:
            logger.error(
                "Unable to find trident CustomResource - Please ensure Trident is installed in Operator Mode"
            )
            raise err

        # Update BackendObject with new values
        patch_backend = trident_backend.to_dict()
        patch_backend["spec"]["svm"] = svm_name
        # Make sure Annotations exist and if not create them before adding new key
        # Note that all annotations need to be strings
        if patch_backend["metadata"].get("annotations", None) is None:
            patch_backend["metadata"]["annotations"] = {}
        patch_backend["metadata"]["annotations"]["trident_mcc_managed"] = str(True)
        patch_backend["metadata"]["annotations"]["trident_mcc_svm_uuid"] = svm_uuid
        patch_backend["metadata"]["annotations"]["trident_mcc_update_count"] = str(
            int(
                patch_backend["metadata"]["annotations"].get(
                    "trident_mcc_update_count", 0
                )
            )
            + 1
        )  # Increment Existing Count to know it is failing over.

        # Patch Backend Api.
        logger.debug(
            f"Attempting to patch TridentBackendConfig named '{patch_backend['metadata']['name']}'"
        )
        try:
            backend_response = trident_backend_api.patch(
                body=patch_backend, content_type="application/merge-patch+json"
            )
        except Exception as err:
            raise err

        logger.info(f"Patch Complete - Validating Result")
        patched_svm_details = self._get_trident_backend_by_name(
            backend_response.metadata.name
        )

        if (
            patched_svm_details.spec.svm == svm_name
            and patched_svm_details.metadata.annotations.get("trident_mcc_svm_uuid", "")
            == svm_uuid
        ):
            logger.info(
                f"Successfully Patched Backend with new svm-name and annotations"
            )
            response = True
        else:
            logger.error(
                f"Unable to patch TridentBackedConfig '{trident_backend.metadata.name}' to correct SVM Name"
            )

        end_time = time.time()
        logger.debug(
            f"_patch_backend_with_svmname execution took {end_time - start_time:.2f}s"
        )
        return response

    def get_na_connection_properties(self, trident_backend_config):
        """Takes Trident Backend Config and Returns a dict that can be passed to NetApp client"""

        response = {"management_lif": trident_backend_config.spec.managementLIF}

        secrets = self._decode_secrets(self._get_backend_secret(trident_backend_config))
        response.update(**secrets)

        return response
