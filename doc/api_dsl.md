Crystal DSL Grammar
===================

**Table of Contents**

- [Overview](#overview)
- [Examples](#examples)
- [Grammar](#grammar)

## Overview

![alt text](http://crystal-sds.org/wp-content/uploads/2016/05/policies-768x180.png "Crystal DSL structure")

SDS policies are means of defining storage services or objectives to be achieved by the system. 
Crystal DSL hides the complexity of low-level policy enforcement, thus achieving simplified storage administration. 
The structure of our DSL is as follows:

**Target**: The target of a policy represents the recipient of a policy’s action (e.g., filter enforcement) and it is mandatory to specify it on every policy definition. In our DSL design, targets can be tenants (projects), containers or even individual data objects.

**Trigger** (optional): Dynamic storage automation policies are characterized by the trigger clause. A policy may have one or more trigger clauses—separated by AND/OR operands—that specify the workload-based situation that will trigger the enforcement of a filter on the target. 
Condition clauses consist of inspection triggers, operands (e.g, >, <, =) and values.

**Action**: The action clause of a SDS policy defines how a filter should be executed on an object request once the policy takes place. 
To this end, the action clause may accept parameters after the WITH keyword in form of key/value pairs that will be passed as input to the filter execution. 
Retaking the example of a compression filter, we may decide to enforce compression using a gzip or an lz4 engine, and even to decide the compression level of these engines. 
In Crystal, filters can be executed at the proxy or at storage nodes (i.e., stages). Our DSL enables to explicitly control the execution stage of a filter in the action clause with the ON keyword. 
For instance, in P1 at the previous figure we may want to execute compression on the proxy to save up bandwidth (ON PROXY) and encrypt the compressed data object on the storage nodes (ON STORAGE_NODE).

Moreover, dynamic storage automation policies can be persistent or transient; a persistent action means that once the policy is triggered the filter enforcement remains indefinitely (default), whereas actions to be executed only during the period where the condition is satisfied are transient (keyword TRANSIENT).

## Examples

- **FOR TENANT:1234567890abcdef DO SET compression**: Apply the compression filter to all objects of tenant '1234567890abcdef'.
- **FOR CONTAINER:1234567890abcdef/container1 DO SET caching ON PROXY**: Apply caching on the proxy server to all objects of the container 'container1' of tenant '1234567890abcdef'. 
- **FOR TENANT:1234567890abcdef WHEN get_ops > 10  DO SET caching**: Apply the caching filter to all objects of tenant '1234567890abcdef' when there are more than 10 GET operations per second (the filter remains indefinitely).
- **FOR TENANT:1234567890abcdef WHEN get_ops > 10  DO SET caching TRANSIENT**: Apply the caching filter to all objects of tenant '1234567890abcdef' only while there are more than 10 GET operations per second.
- **FOR TENANT:1234567890abcdef DO SET compression WITH param1=lz4, SET encryption**: Apply a filter pipeline to all objects of tenant '1234567890abcdef'. For PUT operations, the first filter is compression (with a parameter) and the second one is encyption. For GET operations, filters are applied in reverse order.
- **FOR TENANT:1234567890abcdef DO SET compression TO OBJECT_TYPE=DOCS**: Apply the compression filter to all objects of tenant '1234567890abcdef' that belong to the object type 'DOCS'.
- **FOR TENANT:1234567890abcdef DO SET compression TO OBJECT_SIZE>1024**: Apply the compression filter to all objects of tenant '1234567890abcdef' that are greater than 1024 bytes.

## Grammar

Crystal DSL Grammar in Extended Backus–Naur Form (EBNF): 

```ebnf
rule = 'FOR', target, ['WHEN', condition list], 'DO', action list, ['TO', object list];

target = ( tenant | container | object target | tenant group ) ;

tenant = 'TENANT:', alphanums word ;

container = 'CONTAINER:', alphanums word, '/', alphanumshyphens word ;

object target = 'OBJECT:', alphanums word, '/', alphanumshyphens word, '/', alphanumshyphens word;

tenant group = 'G:', nums word ;

condition list = condition, { logical operator, condition list} ;

logical operator = ( 'AND' | 'OR' ) ;

condition = metric, operand, number ;

operand = ( '<' | '>' | '==' | '!=' | '<=' | '>=' ) ;

action list = action, { ',', action list} ;

action = ( 'SET' | 'DELETE' ), filter, { 'WITH', params list }, { 'ON', server }, { 'TRANSIENT' } ;

params list = param, { ',', params list } ;

param = alphanumsunderscore word, '=', alphanumsunderscore word ; 

server = ( 'PROXY' | 'OBJECT' ) ;

object list = object param, { ',', object list } ;

object param =  object type | object size | ( object type, ',', object size ) | ( object size, ',', object type ) ;

object type = 'OBJECT_TYPE', '=', alphanums word ;

object size = 'OBJECT_SIZE', operand, number ;

alphanums word = alphanums, { alphanums } ;

alphas word = alphas, { alphas } ;

alphanumshyphens word = alphanumshyphens, { alphanumshyphens } ;

alphanumsunderscore word = alphanumsunderscore, { alphanumsunderscore } ;

nums word = nums, { nums } ;

alphanums = ? all alphanumeric characters: all lowercase and uppercase letters and decimal digits ? ;

alphas = ? all lowercase and uppercase letters ? ;

alphanumshyphens = ? all alphanumeric characters plus hyphen and underscore ? ;

alphanumsunderscore = ? all alphanumeric characters plus underscore ? ;

nums = ? all decimal digits ? ;

number = ? A floating point literal ? ;

metric = ? One of the registered metrics ?
 
filter = ? One of the registered filters ?
```