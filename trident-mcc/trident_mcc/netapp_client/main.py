import logging
from socket import SO_VM_SOCKETS_BUFFER_SIZE
import time
from urllib import response
from netapp_ontap import HostConnection, NetAppRestError, utils
from netapp_ontap.resources import Svm

# Enable Debugging of ONTAP
utils.DEBUG = 1

logger = logging.getLogger("trident_mcc.netapp_client")


class NetAppClient:
    def __init__(
        self,
        management_lif: str,
        username: str = None,
        password: str = None,
        cert: str = None,
        key: str = None,
    ):
        # Output details we are intialising Client with - don't actually output credentials
        logger.debug(
            f"Initialising NetApp Client with {management_lif=} username={'redacted' if username else None} password={'redacted' if password else None} cert={'redacted' if cert else None} key={'redacted' if key else None}"
        )
        # Make sure we only have certificate/key or username/password
        if all([username, password]) and not any([cert, key]):
            auth_credentials = {"username": username, "password": password}
        elif all([cert, key]) and not any([username, password]):
            auth_credentials = {"cert": cert, "key": key}
        else:
            logger.error("You must provide either username/password or cert/key")
            raise AttributeError(
                "You must provide either username/password or cert/key"
            )

        # Create Connection
        logger.debug(
            f"Configuring NetApp Connection to Management Lif: {management_lif} "
        )
        self._management_lif = management_lif

        self._connection = HostConnection(
            host=management_lif, verify=False, **auth_credentials
        )

    def _get_svm_collection(self):
        # Get List of SVM's
        logger.info(
            f"Retrieving SVM List from Management Address: {self._management_lif} "
        )
        with self._connection:
            response = [svm for svm in Svm.get_collection()]

        return response

    def _get_svm_details(self, svm):
        """Queries Management Lif for additional SVM details.

        Queries controller for additional SVM details returns name, subtype, state and uuid

        :param svm: Svm object from

        """
        with self._connection:
            svm_details = svm.get()
            if svm_details.is_err == True:
                raise RuntimeError("Error Retrieving SVM Details")
            elif svm_details.is_job == True:
                # This shouldn't happen - so going to raise error here as I don't handle it yet
                logger.error("Retrieving SVM details caused job to be created.")
                raise RuntimeError(
                    "Retrieving SVM Details returned a job, check NetApp system load"
                )
            elif svm_details.is_job == False and svm_details.is_err == False:

                result = {
                    "name": svm.name,
                    "subtype": svm.subtype,
                    "state": svm.state,
                    "uuid": svm.uuid,
                }

        return result or None

    def get_svm(self):
        """Gets Single SVM assuming there is onyl one resolvable."""
        logger.info(
            f"Attempting to resolve SVM Name, UUID and State from Management IP '{self._management_lif}'."
        )
        response = None

        start_time = time.time()

        svm_list = self._get_svm_collection()

        if len(svm_list) > 1:
            logger.error(
                "No SVM Specified and get_collection return more than 1 SVM. Try specifying SVM Name in TridentBackendConfig or use SVM Management Lif instead of cluster."
            )
        elif len(svm_list) == 1:
            svm = svm_list[0]
            logger.info(
                f"Found a single SVM '{svm.name}' on managmenet interface. Retieving Details"
            )
            response = self._get_svm_details(svm)
        end_time = time.time()
        logger.debug(f"get_svm execution took: {end_time - start_time:.2f}s")

        return response or None

    def get_svm_by_name(self, svm_name: str):
        """ """
        logger.info(
            f"Attempting to retrieve SVM details using SVM Name '{svm_name}' from Management IP '{self._management_lif}'."
        )

        response = None

        start_time = time.time()

        # Make sure the SVM name base is what we use (in case we have already appended the new MetroCluster Name -mc)
        if svm_name[-3:].lower() == "-mc":
            svm_base_name = svm_name[:-3].lower()
        else:
            svm_base_name = svm_name.lower()

        svm_list = self._get_svm_collection()

        for svm in svm_list:
            if (
                svm.name.lower() == svm_base_name
                or svm.name.lower() == svm_base_name + "-mc"
            ):
                response = self._get_svm_details(svm)

        end_time = time.time()
        logger.debug(f"get_svm_by_name execution took: {end_time - start_time:.2f}s")

        return response or None

    def get_svm_by_uuid(self, svm_uuid: str):
        """ """
        logger.info(
            f"Attempting to retrieve SVM details using SVM UUID '{svm_uuid}' from Management IP '{self._management_lif}'."
        )

        response = None

        start_time = time.time()

        svm_list = self._get_svm_collection()

        for svm in svm_list:
            if svm.uuid == svm_uuid:
                response = self._get_svm_details(svm)

        end_time = time.time()
        logger.debug(f"get_svm_by_uuid execution took: {end_time - start_time:.2f}s")

        return response or None
