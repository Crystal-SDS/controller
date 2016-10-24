Crystal Controller API Specification - Swift
============================================
**Table of Contents**

- [Enable SDS for a project](#enable-sds-for-a-project)
- [Get a storage policies list](#get-a-storage-policies-list)
- [Create a new storage policy](#create-a-new-storage-policy)
- [Locality](#locality)

#Swift

## Enable SDS for a project

An application can enable Crystal-SDS for a particular project by issuing an HTTP POST request.

### Request

#### URL structure
The URL that represents the tenant resource is
**/swift/tenants**

#### Method
POST

#### Request Query arguments
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**tenant_name** | The project name

#### HTTP Request Example

```
POST /swift/tenants

{
"tenant_name" : "tenantA"
}
```

### Response

#### Response example

```
201 CREATED
```


## Get a storage policies list

An application can retrieve a storage policies list by issuing a HTTP GET request.

### Request

#### URL structure
The URL that represents the storage policies resource is
**/swift/storage_policies**

#### Method
GET

#### HTTP Request Example

```
GET /swift/storage_policies
```

### Response

#### Response example

```
200 OK

[
{"default":"no","name":"s5y6","policy_type":"replication","id":"4"},
{"default":"yes","name":"allnodes","policy_type":"replication","id":"0"},
{"default":"no","name":"s0y1","policy_type":"replication","id":"2"},
{"default":"no","name":"storage4","policy_type":"replication","id":"1"},
{"default":"no","name":"s3y4","policy_type":"replication","id":"3"}
]

```

## Create a new storage policy

An application can create a new ring & storage policy by issuing an HTTP POST request.

### Request

#### URL structure
The URL that represents the storage policies resource is
**/swift/spolicies**

#### Method
POST

#### Request Query arguments
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**storage_node** | A dictionary of location keys and weight values. Location key example: r1z1-{storage_node_management_interface_ip_address}:6000/{device_name}
**policy_id** | The unique ID to identify a policy
**name** | The name of the policy
**partitions** | Number of partitions
**replicas** | Number of replicas. For Erasure coding storage policies, replicas must be equal to the sum of ex_num_data_fragments and ec_num_parity_fragments.
**time** | Time (in hours) between moving a partition more than once
**ec_type** | Optional (only for Erasure Coding storage policies). This specifies the EC scheme that is to be used. Chosen from the list of EC backends provided vy PyECLib 
**ec_num_data_fragments** | Optional (only for Erasure Coding storage policies). The total number of fragments that will be comprised of data.
**ec_num_parity_fragments** | Optional (only for Erasure Coding storage policies). The total number of fragments that will be comprised of parity.
**ec_object_segment_size** | Optional (only for Erasure Coding storage policies). The amount of data that will be buffered up before feeding a segment into the encoder/decoder.

#### HTTP Request Example

```
POST /swift/spolicies

{
"storage_node": {"r1z1-192.168.1.5:6000/sdb1":"200", "r1z1-192.168.1.6:6000/sdb2":"200"},
"policy_id": 5,
"name": "ec104",
"partitions": 4,
"replicas": 14,
"time": 1
"ec_type": "liberasurecode_rs_vand",
"ec_num_data_fragments": 10,
"ec_num_parity_fragments": 4,
"ec_object_segment_size": 1048576
}
```

### Response

#### Response example

```
201 CREATED
```

## Locality

An application can ask for the location of specific account/container/object by issuing an HTTP GET request.

### Request

#### URL structure
The URL that represents the locality resource is
**/swift/locality/{project}/{container}/{swift_object}**
**Note:** It's mandatory to enter the **project** parameter. **container** and **swift_object** are optional.

#### Method
GET

#### HTTP Request Example

```
Content-Type: application/json

GET /swift/locality/AUTH_151542dfdsa541asd455fasf1/test1/file.txt
```

### Response

#### Response example

```json

200 OK
{
  "headers": {
    "X-Backend-Storage-Policy-Index": "0"
  },
  "endpoints": [
    "http://127.0.0.1:6010/sdb1/867/AUTH_151542dfdsa541asd455fasf1/test1/file.txt",
    "http://127.0.0.1:6020/sdb2/867/AUTH_151542dfdsa541asd455fasf1/test1/file.txt",
    "http://127.0.0.1:6040/sdb4/867/AUTH_151542dfdsa541asd455fasf1/test1/file.txt"
  ]
}
```

