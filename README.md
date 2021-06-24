# trident_mcc
This project is to attempt to detect that a configured NetApp Tridnet Backend has failed 
over, and reapply the configuration file for that backed.

## Purpose
Currently when using NetApp Trident with Metrocluster configurations, if the svm fails over to
the other nodes in the MCC the svm name changes, when this happens trident is not longer able 
to manage volumes on this svm. Though underlying storage access to these volumes continues fine.

## Project Parameters
  1. Needs to run as a container under the k8s infrastructure
  2. Needs to be able to be configured using a file / configmap from k8s
  3. Needs a way to automatically monitor above configmaps, detect a change and reload configuration on change
  4. Needs to monitor the SVM connection based on the defined backend and detect an MCC failover (maybe SVM name, maybe there is something more useful in the Api, will work that out)
  5. If detects MCC failover - reapply the backend config - without modification (or with renaming the SVM).


Ideally no credentials will be stored and will just use the stored cluster credentials using the k8s secrets and the trident operator for in cluster backend definitions.


