SDS Controller API Specification - Registry
===========================================
**Table of Contents**

- [Error handling](#error-handling)
- [Authentication](#authentication)
- [Metrics Workload](#metrics-workload)
  - [Add a workload metric](#add-a-workload-metric)
  - [Get all workload metrics](#get-all-workload-metrics)
  - [Update a workload metric](#update-a-workload-metric)
  - [Get metric metadata](get-metric-metadata)
  - [Delete a workload metric](#delete-a-workload-metric)
- [Filters](#metrics-workload)
  - [Add a filter](#add-a-filter)
  - [Get all filters](#get-all-filters)
  - [Update a filter](#update-a-filter)
  - [Get filter metadata](#get-filter-metadata)
  - [Delete a filter](#delete-a-filter)
- [Tenants group](#tenants-group)
  - [Add a tenants group](#add-a-tenants-group)
  - [Get all tenants groups](#get-all-tenants-groups)
  - [Get tenants of a group](#get-tenants-of-a-group)
  - [Add a member to a tenants group](#add-a-member-to-a-tenants-group)
  - [Delete a tenants group](#delete-a-tenants-group)
  - [Delete a member of a tenants group](#delete a member of a tenants group)


#Error handling

Errors are returned using standard HTTP error code syntax. Any additional info is included in the body of the return call, JSON-formatted. Error codes not listed here are in the REST API methods listed below.

Standard API errors

CODE |  DESCRIPTION
--- | ---
**400** | Bad input parameter. Error message should indicate which one and why.
**401** | Authorization required. The presented credentials, if any, were not sufficient to access the folder resource. Returned if an application attempts to use an access token after it has expired.
**403** | Forbidden. The requester does not have permission to access the specified resource.
**404** | File or folder not found at the specified path.
**405** | Request method not expected (generally should be GET or POST).
**5xx** | Server error


#Authentication

After successfully receiving the credentials from keystone, it is necessary that all the calls of the API will be authenticated. To authenticate the calls, it needs to add the header explained in the next table:

OAuth PARAMETER |  DESCRIPTION
--- | ---
**X-Auth-Token** | Admin token obtained after a successful authentication in keystone.

#Metrics Workload

## Add a workload metric

An application can registry a metric workload by issuing an HTTP POST request. The application needs to provide the metric workload metadata like json format.

### Request

#### URL structure
The URL is **/registry/metrics.**

#### Method
POST

#### Request Query arguments
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**name** | The name is the keyword to be used in condition clauses of storage policy definitions. Workload metric names should be unique and self-descriptive to ease the design of storage policies.
**network location** | This requires the metadata information of a workload metric to provide the network location to reach the process and obtain the computed metric.
**metric type** | Workload metric’s metadata should define the type of metric produces, such a integer or a boolean, to enable the DSL syntax checker to infer if values in condition clauses belong to the appropriate type.

#### HTTP Request Example

```
POST /registry/metrics
```

### Response

#### Response example

```json

Response <201>
TODO
```
## Get all workload metrics

An application can get all the metrics registered by issuing an HTTP GET request.

### Request

#### URL structure
The URL is **/registry/metrics**


#### Method
GET

#### HTTP Request Example

```
GET /registry/metrics

```
### Response

#### Response example

```json

Response <201>
[{
"name":"througput",
"network_location":"10.30.102.102",
"type":"bool",
},{
"name":"slowdown",
"network_location":"10.30.102.102",
"type":"bool",
}]
```

## Update a workload metric

An application can update the metadata of a workload metric by issuing an HTTP PUT request.

### Request

#### URL structure
The URL is **/registry/metrics/:metric_id**

#### Method
PUT

#### HTTP Request Example

```json
PUT /registry/metrics/througput
{
  "network_location":"10.30.103.103"
}
```

### Response

#### Response example

```json

Response <201>
{
"name":"througput",
"network_location":"10.30.102.102",
"type":"bool",
}
```

## Get metric metadata

An application can ask for a workload metric metadata by issuing an HTTP GET request.

### Request

#### URL structure
The URL is **/registry/metrics/:metric_id**

#### Method
GET

#### HTTP Request Example

```
GET /registry/metrics/througput
```
### Response

#### Response example

```json

HTTP/1.1 200 OK
Content-Type: application/json; charset=UTF-8
Content-Length: 248

{
"name":"througput",
"network_location":"10.30.102.102",
"type":"bool",
}
```

## Delete a workload metric

An application can delete a workload metric by issuing an HTTP GET request.

### Request

#### URL structure
The URL is **/registry/metrics/:metric_id**

#### Method
DELETE

#### HTTP Request Example

```
DELETE /registry/metrics/througput

```

### Response

#### Response example

```json

HTTP/1.1 204 OK
Content-Type: application/json; charset=UTF-8
Content-Length: 248

```

#Filters

## Add a filter

An application can registry a filter by issuing an HTTP POST request. The application needs to provide the filter metadata like json format.

### Request

#### URL structure
The URL is **/registry/filters.**

#### Method
POST

#### Request Query arguments
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**name** | Filter names should be unique and self-descriptive to ease the design of storage policies.
**identifier** | The identifier field is only required by out filter framework for object storage based on Storlets **(Optional)**
**activation_url** | Different filter types may have distinct calls from the SDS Controller API viewpoint, we need to provide the base URL to be used to trigger the filter activation.
**valid_parameters** | Dictionary where the keys are the parameters accepted by the filter, and the values are the type (i.e. boolean, integer) of each parameter.

#### HTTP Request Example

```
POST /registry/filters
```

### Response

#### Response example

```json
POST /registry/filters
Response <201>
{
"name":"compress",
"identifier":2,
"activation_url":"http://sds_controller/filters/1",
"valid_parameters":{"param1":"bool", "param2":"integer"}
}
```

## Get all filters

An application can get all filters registered by issuing an HTTP PUT request.

### Request

#### URL structure
The URL is **/registry/filters**


#### Method
GET

#### HTTP Request Example

```
GET /registry/filters

```
### Response

#### Response example

```json

Response <201>
[{
  "name":"compress",
  "identifier":2,
  "activation_url":"http://sds_controller/filters/1",
  "valid_parameters":{"param1":"bool", "param2":"integer"}
},{
  "name":"compress_gzip",
  "identifier":2,
  "activation_url":"http://sds_controller/filters/1",
  "valid_parameters":{"param1":"bool", "param2":"integer"}
}]
```

## Update a filter

An application can update the metadata of a filter by issuing an HTTP PUT request.

### Request

#### URL structure
The URL is **/registry/filters/:filter_name**

#### Method
PUT

#### HTTP Request Example

```json
PUT /registry/filters/compress
{
"activation_url":"http://sds_controller/filters/2"
}
```

### Response

#### Response example

```json

Response <201>
{
  "name":"compress",
  "identifier":2,
  "activation_url":"http://sds_controller/filters/2",
  "valid_parameters":{"param1":"bool", "param2":"integer"}
}
```

## Get filter metadata

An application can ask for a filter metadata by issuing an HTTP GET request.

### Request

#### URL structure
The URL is **/registry/filters/:filter_name**

#### Method
GET

#### HTTP Request Example

```
GET /registry/filters/compress
```
### Response

#### Response example

```json

HTTP/1.1 200 OK
Content-Type: application/json; charset=UTF-8
Content-Length: 248

{
  "name":"compress",
  "identifier":2,
  "activation_url":"http://sds_controller/filters/2",
  "valid_parameters":{"param1":"bool", "param2":"integer"}
}
```

## Delete a filter

An application can delete a filter by issuing an HTTP GET request.

### Request

#### URL structure
The URL is **/registry/filters/:filter_name**

#### Method
DELETE

#### HTTP Request Example

```
DELETE /registry/filters/compress

```

### Response

#### Response example

```json


HTTP/1.1 204 OK
Content-Type: application/json; charset=UTF-8
Content-Length: 248

```




#Tenants group

## Add a tenants group

An application can registry a tenants group by issuing an HTTP POST request. The application needs to provide the filter metadata like json format.

### Request

#### URL structure
The URL is **/registry/filters.**

#### Method
POST

#### Request Query arguments
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**name** | Filter names should be unique and self-descriptive to ease the design of storage policies.
**identifier** | The identifier field is only required by out filter framework for object storage based on Storlets **(Optional)**
**activation_url** | Different filter types may have distinct calls from the SDS Controller API viewpoint, we need to provide the base URL to be used to trigger the filter activation.
**valid_parameters** | Dictionary where the keys are the parameters accepted by the filter, and the values are the type (i.e. boolean, integer) of each parameter.

#### HTTP Request Example

```
POST /registry/filters
```

### Response

#### Response example

```json
POST /registry/filters
Response <201>
{
"name":"compress",
"identifier":2,
"activation_url":"http://sds_controller/filters/1",
"valid_parameters":{"param1":"bool", "param2":"integer"}
}
```

## Get all tenants group

An application can get all tenant groups registered by issuing an HTTP GET request.

### Request

#### URL structure
The URL is **/registry/gtenants**


#### Method
GET

#### HTTP Request Example

```
GET /registry/gtenants

```
### Response

#### Response example

```json

Response <201>
{
  "G:2": [
    "4",
    "5",
    "6"
  ],
  "G:1": [
    "1",
    "2",
    "3"
  ]
}
```

## Get tenants of a group

An application can get all tenants of a group registered by issuing an HTTP GET request.

### Request

#### URL structure
The URL is **/registry/gtenants/gtenant_id**


#### Method
GET

#### HTTP Request Example

```
GET /registry/gtenants/1

```
### Response

#### Response example

```json

Response <201>
[
  "4",
  "5",
  "6"
]
```

## Add a member to a tenants group

An application can add members to a group by issuing an HTTP PUT request.

### Request

#### URL structure
The URL is **/registry/gtenants/gtenant_id**

#### Method
PUT

#### HTTP Request Example

```json
PUT /registry/gtenants/2

["8", "9"]

```

### Response

#### Response example

```json

Response <201>

The members of the tenants group with id: 2 has been updated
```

## Delete a tenants group

An application can delete a tenants group by issuing an HTTP DELETE request.

### Request

#### URL structure
The URL is **/registry/gtenants/:gtenant_id**

#### Method
DELETE

#### HTTP Request Example

```
DELETE /registry/gtenants/2

```

### Response

#### Response example

```json

HTTP/1.1 204 NO CONTENT

```

## Delete a member of a tenants group

An application can delete a member of a tenants group by issuing an HTTP DELETE request.

### Request

#### URL structure
The URL is **/registry/gtenants/:gtenant_id/tenants/:tenant_id**

#### Method
DELETE

#### HTTP Request Example

```
DELETE /registry/gtenants/2/tenants/2

```

### Response

#### Response example

```json

HTTP/1.1 204 NO CONTENT

```
