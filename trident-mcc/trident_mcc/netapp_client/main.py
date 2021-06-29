import logging
from netapp_ontap import config, HostConnection, NetAppRestError, utils
from netapp_ontap.resources import Svm

# Enable Debugging of ONTAP
utils.DEBUG = 1

logger = logging.getLogger("trident_mcc.netapp_client")


def get_svm_details(
    svm_uuid: str,
    management_lif: str,
    username: str = None,
    password: str = None,
    cert: str = None,
    key: str = None,
):
    """"""

    # Make sure we only have certificate/key or username/password
    if all([username, password]) and not any([cert, key]):
        auth_credentials = {"username": username, "password": password}
    elif all([cert, key]) and not any([username, password]):
        auth_credentials = {"cert": cert, "key": key}
    else:
        logger.error("You must provide either username/password or cert/key")
        raise AttributeError("You must provide either username/password or cert/key")

    # Create Connection
    logger.debug(f"Configuring NetApp Connection to Management Lif: {management_lif} ")
    config.CONNECTION = HostConnection(
        host=management_lif, verify=False, **auth_credentials
    )

    # Get List of SVM's
    logger.info(f"Retrieving SVM List from Management Address: {management_lif} ")
    response = Svm.get_collection()

    result = {}

    for svm in response:
        print(dir(svm))
        print(svm)
        print(f"k8s - {svm_uuid=} = netapp {svm.uuid=} ")
        if svm.uuid == svm_uuid:
            svm_details = svm.get()
            if svm_details.is_err == True:
                raise RuntimeError("Error Retrieving SVM Details")
            elif svm_details.is_job == True:
                # This shouldn't happen - so going to raise error here as I don't handle it yet
                # TODO: Conver to Async and put an Async retry handler
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

    return result

    # for record in response:
    #     svm_list.append(record)

    # for svm in svm_list:
    #     if svm.uuid =
    #     # response = svm.get()
    #     # if response.is_job == False and response.is_err == False:
    #     #     print(f"{svm.name=},{svm.subtype=},{svm.state=},{svm.uuid=}")


#
#   Svm(
#     {'fcp': {'enabled': False, 'allowed': True},
#     'uuid': 'aa72ef62-cd19-11eb-96a2-00a0b8f5950d',
#     'aggregates': [{'uuid': 'dc606d90-29a4-4196-b739-2f576cea29e1', 'name': 'test01'}],
#     's3': {'enabled': False},
#     'iscsi': {'enabled': False, 'allowed': True},
#     'nis': {'enabled': False},
#     'snapshot_policy': {'uuid': '27594d11-cd18-11eb-96a2-00a0b8f5950d', '_links': {'self': {'href': '/api/storage/snapshot-policies/27594d11-cd18-11eb-96a2-00a0b8f5950d'}}, 'name': 'default'},
#     'max_volumes': 'unlimited',
#     'name': 'k8s_01',
#     'aggregates_delegated': True,
#     'language': 'en.utf_8',
#     'nsswitch': {'hosts': ['files', 'dns'], 'netgroup': ['files'], 'namemap': ['files'], 'passwd': ['files'], 'group': ['files']},
#     'nfs': {'enabled': True, '_links': {'self': {'href': '/api/protocols/nfs/services/aa72ef62-cd19-11eb-96a2-00a0b8f5950d'}}, 'allowed': True},
#     'ldap': {'enabled': False},
#     'cifs': {'enabled': False, 'allowed': True},
#     'subtype': 'default',
#     'ip_interfaces': [
#         {
#             'name': 'lif_k8s_01_362',
#             'uuid': 'b66a6554-cd19-11eb-96a2-00a0b8f5950d',
#             'services': ['data_core', 'data_nfs', 'data_fpolicy_client'],
#             'ip': {'address': '192.168.20.225'},
#             '_links': {
#                 'self': {
#                     'href': '/api/network/ip/interfaces/b66a6554-cd19-11eb-96a2-00a0b8f5950d'
#                 }
#             }
#         },
#         {
#             'name': 'lif_k8s_01_716',
#             'uuid': 'b09a5905-d263-11eb-96a2-00a0b8f5950d',
#             'services': ['data_core', 'management_ssh', 'management_https'],
#             'ip': {'address': '192.168.20.224'},
#             '_links': {'self': {'href': '/api/network/ip/interfaces/b09a5905-d263-11eb-96a2-00a0b8f5950d'}}
#         }
#     ],
#     'certificate': {
#         'uuid': 'b5b9b1e3-cd19-11eb-96a2-00a0b8f5950d',
#         '_links': {
#             'self': {
#                 'href': '/api/security/certificates/b5b9b1e3-cd19-11eb-96a2-00a0b8f5950d'
#             }
#         }
#     },
#     'comment': '',
#     'nvme': {'enabled': False, 'allowed': False},
#     '_links': {
#         'self': {
#             'href': '/api/svm/svms/aa72ef62-cd19-11eb-96a2-00a0b8f5950d'
#         }
#     },
#     'state': 'running'}
#     )
#


# for svm in svm

# response = Svm.get()


# for record in Svm.get_collection(connection=HostConnection):
#     print(f"get_collections returns type {type(record)}")
#     print(f"{record=}")