Crystal DSL Grammar
===================

## Overview

![alt text](http://crystal-sds.org/wp-content/uploads/2016/05/policies-768x180.png "Crystal DSL structure")

SDS policies are means of defining storage services or objectives to be achieved by the system. 
Crystal DSL hides the complexity of low-level policy enforcement, thus achieving simplified storage administration. 
The structure of our DSL is as follows:

Target: The target of a policy represents the recipient of a policy’s action (e.g., filter enforcement) and it is mandatory to specify it on every policy definition. In our DSL design, targets can be tenants (projects), containers or even individual data objects.

Trigger (optional): Dynamic storage automation policies are characterized by the trigger clause. A policy may have one or more trigger clauses—separated by AND/OR operands—that specify the workload-based situation that will trigger the enforcement of a filter on the target. 
Condition clauses consist of inspection triggers, operands (e.g, >, <, =) and values.

Action: The action clause of a SDS policy defines how a filter should be executed on an object request once the policy takes place. 
To this end, the action clause may accept parameters after the WITH keyword in form of key/value pairs that will be passed as input to the filter execution. 
Retaking the example of a compression filter, we may decide to enforce compression using a gzip or an lz4 engine, and even to decide the compression level of these engines. 
In Crystal, filters can be executed at the proxy or at storage nodes (i.e., stages). Our DSL enables to explicitly control the execution stage of a filter in the action clause with the ON keyword. 
For instance, in P1 at the previous figure we may want to execute compression on the proxy to save up bandwidth (ON PROXY) and encrypt the compressed data object on the storage nodes (ON STORAGE_NODE).

Moreover, dynamic storage automation policies can be persistent or transient; a persistent action means that once the policy is triggered the filter enforcement remains indefinitely (keyword PERSISTENT, default), whereas actions to be executed only during the period where the condition is satisfied are transient (keyword TRANSIENT). 

## Grammar

TODO