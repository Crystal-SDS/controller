Crystal Controller API Specification - Swift
============================================
**Table of Contents**

- [Enable SDS for a project](#enable-sds-for-a-project)
- [Get a storage policies list](#get-a-storage-policies-list)
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

## Locality

An application can ask for the location of specific account/container/object by issuing an HTTP GET request.

### Request

#### URL structure
The URL that represents the locality resource is
**/swift/locality/:project/:container/:swift_object**
**Note:** It's mandatory to enter the project parameter. Container and swift_object are optional.

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
