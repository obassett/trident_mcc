# trident_mcc

## Table of Contents
- [trident_mcc](#trident_mcc)
  - [Table of Contents](#table-of-contents)
  - [Background](#background)
    - [What is Trident?](#what-is-trident)
    - [What is Metrocluster?](#what-is-metrocluster)
  - [Purpose](#purpose)
    - [How does trident_mcc resolve this?](#how-does-trident_mcc-resolve-this)
  - [Installation](#installation)
    - [All in One YAML deployment](#all-in-one-yaml-deployment)
    - [Environment Variables](#environment-variables)
  - [Issues and Contributions](#issues-and-contributions)


## Background
This project attempts to resolve a current issue when using NetApp Trident with 
NetApp Metrocluster. The issue occurs when the Metrocluster fails-over. At the 
point of the fail-over, although all the data volumes continue to function the 
abilty for Trident to manage the volume life-cycles - provisioning, deleting, 
updating.

### What is Trident?  
From the [NetApp Trident Docs](https://netapp-trident.readthedocs.io/):

>Trident is a fully supported open source project maintained by NetApp. It has 
>been designed from the ground up to help you meet your containerized applications’ 
>persistence demands using industry-standard interfaces, such as the Container 
>Storage Interface (CSI).

>Trident deploys in Kubernetes clusters as pods and provides dynamic storage 
>orchestration services for your Kubernetes workloads. It enables your containerized 
>applications to quickly and easily consume persistent storage from NetApp’s broad 
>portfolio that includes ONTAP (AFF/FAS/Select/Cloud), Element software (HCI/SolidFire),
>and SANtricity (E/EF-Series) data management software, as well as the Azure NetApp 
>Files service, Cloud Volumes Service on Google Cloud, and the Cloud Volumes Service on AWS.


### What is Metrocluster?
From  the [NetApp Website](https://www.netapp.com/support-and-training/documentation/metrocluster/):

>NetApp® MetroCluster™ configurations combine array-based clustering with synchronous 
>replication to deliver continuous availability, immediately duplicating all of your 
>mission-critical data on a transaction-by-transaction basis. MetroCluster configurations
>enhance the built-in high availability and nondisruptive operations of NetApp hardware 
>and ONTAP® storage software, providing an additional layer of protection for the entire 
>storage and host environment.


## Purpose
Currently when using Trident with Metrocluster configurations, if the Storage 
Virtual Machine (SVM) fails over to the other nodes in the Metrocluster the 
SVM name changes, when this happens Trident is no longer able to manage volumes 
on this SVM. Though underlying storage access to these volumes continues correctly.

### How does trident_mcc resolve this?
This project deploys as a kubernetes pod alongside trident in the trident namespace. 
At a set polling interval it queries the kubernertes API for all the TridentBackendConfig 
objects, and then connects to the backend to validate the SVM name in the TridentBackendConfiguration
matches the actaul SVM name, if it doesn't it updates the TridentBackendConfiguration.

>Note: The first time trident_mcc runs on a given TridentBackendConfig -  if no SVM configuration is 
>specified then it will add one based on the current SVM name when it queries the backend.


## Installation
The trident_mcc project requires permissions to the following resources:
  - Cluster Scoped:
    - namespaces - GET and LIST - To validate the trident namespace
  - Namespace Scoped:
    - secrets - GET, HEAD, and LIST - To get the credentials for the backend storage
    - tridentbackendconfigs.trident.netapp.io - GET, HEAD, PATCH and LIST - To get and modify the Trident Backend Configuration


### All in One YAML deployment
If your trident installation uses the trident namespace (by default) then you can run the following to install trident_mcc:

```
kubectl apply -f https://github.com/obassett/trident_mcc/raw/main/deployment/trident-mcc-full-deployment.yaml
```
This will create the service account, roles. bindings and then finally the deployment.

If you are not using the default 'trident' namespace, then you can download this file and update with the correct namespace

### Environment Variables
Inside of the deployment there are several environment variables you can set to affect the code.

| Name                 | Type                  | Default | Description                                                                                                                                                                                                                                             |
| -------------------- | --------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DEBUG                | -                     | -       | If this environment variable is set to anything then full debug logging will be enabled. Entirely remove if you don't want Debug logging.                                                                                                               |
| POLLING_INTERVAL     | Int (should be >= 10) | 300     | The number in seconds for which to Poll the Kubernetes Namespace. It is recommended that it be no less than 10 seconds.                                                                                                                                 |
| TRIDENT_NAMESPACE    | String                | trident | The name of the trident namespace                                                                                                                                                                                                                       |
| KUBE_CONFIG_LOCATION | String                | -       | This should not be set in a kubernetes deployment of trident_mcc and is only used if running the python directly. If not set then trident_mcc will use the service account specified in the deplyoment configuration and use the in-cluster credentials |

## Issues and Contributions
Please feel free to create github issues and pull requests.


