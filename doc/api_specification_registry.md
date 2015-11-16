SDS Controller API Specification - Registry
===========================================
**Table of Contents**

- [Error handling](#error-handling)
- [Authentication](#authentication)
- [Filters](#Filters)
  - [Create a Filter](#create-a-filter)
  - [Upload a Filter data](#upload-a-filter-data)
  - [Delete a Filter](#delete-a-filter)
  - [Get Filter metadata](#get-filter-metadata)
  - [List Filters](#list-filters)
  - [Update Filter metadata](#update-filter-metadata)
  - [Deploy a Filter](#deploy-a-filter)
  - [Undeploy a Filter](#undeploy-a-filter)
  - [List deployed Filters of an account](#list-deployed-filters-of-an-account)
- [Dependencies](#dependencies)
  - [Create a Dependency](#create-a-dependency)
  - [Upload a Dependency Data](#upload-a-dependency-data)
  - [Delete a Dependency](#delete-a-dependency)
  - [Get Dependency metadata](#get-dependency-metadata)
  - [List Dependencies](#list-dependencies)
  - [Update Dependency metadata](#update-dependency-metadata)
  - [Deploy Dependency](#deploy_dependency)
  - [Undeploy a Dependency](#undeploy-a-dependency)
  - [List deployed Dependencies of an Account](#list-deployed-dependencies-of-an-account)

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

#Filters

## Create a filter

An application can create a filter by issuing an HTTP POST request. The application needs to provide the filter metadata like json format. The binary file will be uploaded after this call, first it must upload the metadata fields.

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
**/filters.**

#### Method
POST

#### Request Query arguments
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**name** | The name of the filter to be created.
**language** |Currently must be 'java'
**interface_version** | Currently we have a single version '1.0'
**dependencies** | A comma separated list of dependencies. Default: “ ”
**object_metadata** | Currently, not in use, but must appear. Use the value 'no'
**main** | The name of the class that implements the IStorlet API. In our case: 'com.ibm.filter.identity.Identityfilter'

#### HTTP Request Example

```
POST /filters
```

### Response

#### Response example

```json

Response <201>
{
"id":1345,
"name":"filterName",
"language":"Java",
"interface_version":"1.0",
"dependencies":"’’",
"object_metadata":"no",
"main":"com.urv.filter.uonetrace.UOneTracefilter",
"deployed":"false"
}
```
## Upload a filter data

An application can upload a filter data by issuing an HTTP PUT request. The application needs to provide the filter data like  a QueryDicct with a single key 'file' containing the upload file.
**media_type:** `multipart/form-data`

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
**/filters/:filter_id/data**.

#### Method
PUT

#### Request Headers

The request header includes the following information:

FIELD |  DESCRIPTION
--- | ---
**X-Auth-Token** | Token to authenticate to OpenStack Swift as an **Admin**
**enctype** | The content type and character encoding of the response. The content type must be **multipart/form-data**.

#### HTTP Request Example

```
PUT /filters/:filter_id/data
"media_type":"multipart/form-data"
{'file':<binary file>} (QueryDicct)

```

## Delete a filter

An application can delete a filter by issuing an HTTP DELETE request. This call delete the filter from SDS Controller store, **BUT** it does not undeploy this filter from OpenStack Swift. Therefore, some users could maintain activated this filter in their account after delete the filter from SDS Controller.

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
**/filters/:filter_id.**

#### Method
DELETE

#### HTTP Request Example

```
DELETE /filters/:filter_id
```

## Get filter metadata

An application can ask for the filter metadata by issuing an HTTP GET request.

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
**/filters/:filter_id**

#### Method
GET

#### HTTP Request Example

```
GET /filters/:filter_id
```
### Response

#### Response example

```json

HTTP/1.1 200 OK
Content-Type: application/json; charset=UTF-8
Content-Length: 248

{
"id":1345,
"name":"filterName",
"language":"Java",
"interface_version":"1.0",
"dependencies":"’’",
"object_metadata":"no",
"main":"com.urv.filter.uonetrace.UOneTracefilter"
}


```

## List Filters

An application can list the Filters by issuing an HTTP GET request.

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
**/filters**

#### Method
GET

#### HTTP Request Example

```
GET /filters

```

### Response

#### Response example

```json


HTTP/1.1 200 OK
Content-Type: application/json; charset=UTF-8
Content-Length: 248

[
{
"id":1345,
"name":"filterName",
"language":"Java",
"interface_version":"1.0",
"dependencies":"’’",
"object_metadata":"no",
"main":"com.urv.filter.uonetrace.UOneTracefilter"
},{
"id":1345,
"name":"filterName",
"language":"Java",
"interface_version":"1.0",
"dependencies":"’’",
"object_metadata":"no",
"main":"com.urv.filter.uonetrace.UOneTracefilter"
},{
"id":1345,
"name":"filterName",
"language":"Java",
"interface_version":"1.0",
"dependencies":"’’",
"object_metadata":"no",
"main":"com.urv.filter.uonetrace.UOneTracefilter"
}
]

```
## Update filter metadata

An application can update the filter metadata by issuing an HTTP PUT request.

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
 **/filters/:filter_id**.

#### Method
PUT

#### Request Body
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**name** | The name of the filter to be created.
**language** |Currently must be 'java'
**interface_version** | Currently we have a single version '1.0'
**dependencies** | A comma separated list of dependencies. Default: “ ”
**object_metadata** | Currently, not in use, but must appear. Use the value 'no'
**main** | The name of the class that implements the Ifilter API. In our case: 'com.ibm.filter.identity.Identityfilter'

#### HTTP Request Example

```json

PUT filters/32565632156

Content-Length: 294
Content-Type: application/json

{
"name":"filterName",
"language":"Java",
"interface_version":"1.0",
"dependencies":"’’",
"object_metadata":"no",
"main":"com.urv.filter.uonetrace.UOneTracefilter",
}

```
### Response

#### Response example

```json

HTTP/1.1 200 OK
Content-Type: application/json; charset=UTF-8
Content-Length: 248

{
"name":"filterName",
"language":"Java",
"interface_version":"1.0",
"dependencies":"’’",
"object_metadata":"no",
"main":"com.urv.filter.uonetrace.UOneTracefilter"
}

```

## Deploy a filter

An application can deploy the filter to Swift by issuing an HTTP PUT request.

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
**/filters/:account/deploy/:filter_id/**

#### Method
PUT


#### Request Headers

The request header includes the following information:

FIELD |  DESCRIPTION
--- | ---
**X-Auth-Token** | Token to authenticate to OpenStack Swift as an **Admin**

#### Request Body
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**params** | The parameters needed by the filter execution. These parameters are codified as query string.


#### HTTP Request Example

```json
Content-Type: application/json
PUT /filters/4f0279da74ef4584a29dc72c835fe2c9/deploy/3

{
"params":"select=user_id, type=string",
}
```

### Response

#### Response example

```json

HTTP/1.1 201 Created

```
## Undeploy filter

An application can undeploy the filter of an account from Swift by issuing an HTTP PUT request.

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
**/filters/:account/undeploy/:dependency_id/**

#### Method
PUT

#### Request Headers

The request header includes the following information:

FIELD |  DESCRIPTION
--- | ---
**X-Auth-Token** | Token to authenticate to OpenStack Swift as an **Admin**

#### HTTP Request Example

```json
Content-Type: application/json
POST /filters/4f0279da74ef4584a29dc72c835fe2c9/undeploy/3

```

## List deployed Filters of an Account

An application can list all the deployed Filters of an account to Swift by issuing an HTTP GET request.

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
**/filters/:account/deploy/**

#### Method
GET

#### Request Headers

The request header includes the following information:

FIELD |  DESCRIPTION
--- | ---
**X-Auth-Token** | Token to authenticate to OpenStack Swift as an **Admin**

#### HTTP Request Example

```json
Content-Length: 294
Content-Type: application/json
GET /filters/123/deploy/

```

# Dependencies
## Create a Dependency

An application can create a Dependency by issuing an HTTP POST request. The application needs to provide the Dependency metadata like json format. The binary file will be uploaded after this call, first it must upload the metadata fields.

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
**/filters/dependencies.**
#### Method
POST

#### Request Body
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**name** | The name of the dependency to be created. It is a unique field.
**version** | While the engine currently does not parse this header, it must appear.
**permissions** | An optional metadata field, where the user can state the permissions given to the dependency when it is copied to the Linux container. This is helpful for binary dependencies invoked by the filter. For a binary dependency once can specify: '0755'

#### HTTP Request Example

```
POST /filters/dependencies

{
"name":"DependencyName",
"version":"1.0",
"permissions":"0755"
}
```

### Response

#### Response example

```json

HTTP/1.1 200 OK
Content-Type: application/json; charset=UTF-8
Content-Length: 248

{
"id":1345,
"name":"DependencyName",
"version":"1.0",
"permissions":"0755"
}

```

## Upload a Dependency

An application can upload a Dependency data by issuing an HTTP PUT request. The application needs to provide the dependency data like  a QueryDicct with a single key 'file' containing the upload file.
**media_type:** `multipart/form-data`


### Request

#### URL structure
The URL that represents the filter data resource. The URL is
**/filters/dependencies/:dependency_id/data.**

#### Method
PUT

#### HTTP Request Example

```
PUT /filters/dependencies/:dependency_id/data
"media_type":"multipart/form-data"

{'file':<binary file>} (QueryDicct)
```

### Response

#### Response example

```json

HTTP/1.1 200 OK

```

## Delete a Dependency

An application can delete a Dependency by issuing an HTTP DELETE request. This call delete the Dependency from Swift and SDS Controller.

### Request

#### URL structure

The URL that represents the filter data resource. The URL is
**/filters/dependencies/:filter_id.**

#### Method
DELETE


#### HTTP Request Example

```
DELETE /filters/dependencies/:dependency_id
```

## Get Dependency metadata

An application can ask for the Dependency metadata by issuing an HTTP GET request.

### Request

#### URL structure

The URL that represents the filter data resource. The URL is
**/filters/dependencies/:filter_id**

#### Method
GET

#### HTTP Request Example

```
GET /filters/dependencies/:dependency_id
Content-Type: application/json; charset=UTF-8
```

### Response

#### Response example

```json

HTTP/1.1 200 OK
Content-Type: application/json; charset=UTF-8

{
"id":1345,
"name":"DependencyName",
"version":"1.0",
"permissions":"0755"
}
```

## List Dependencies

An application can list the Dependencies by issuing an HTTP GET request.

### Request

#### URL structure

The URL that represents the filter data resource. The URL is
**/sotrlets/dependencies**

#### Method
GET

#### HTTP Request Example

```
Content-Type: application/json; charset=UTF-8
GET /filters

```
### Response

#### Response example

```json

HTTP/1.1 200 OK
Content-Type: application/json; charset=UTF-8
Content-Length: 248

[
{
"id":1345,
"name":"DependencyName",
"version":"1.0",
"permissions":"0755"
},{
"id":1345,
"name":"DependencyName",
"version":"1.0",
"permissions":"0755"
},{
"id":1345,
"name":"DependencyName",
"version":"1.0",
"permissions":"0755"
}
]
```

## Update Dependency metadata

An application can update the Dependency metadata by issuing an HTTP PUT request.

### Request

#### URL structure

The URL that represents the dependency data resource. The URL is
**/filters/dependencies/:dependency_id**


#### Method
PUT

#### Request Query arguments
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**name** | The name of the dependency to be created. It is a unique field.
**version** | While the engine currently does not parse this header, it must appear.
**permissions** | An optional metadata field, where the user can state the permissions given to the dependency when it is copied to the Linux container. This is helpful for binary dependencies invoked by the filter. For a binary dependency once can specify: '0755'

#### HTTP Request Example
```json
PUT /filters/dependencies/123
{
"name":"DependencyName",
"version":"1.0",
"permissions":"0755"
}
```
### Response

#### Response example

```json
HTTP/1.1 200 OK
Content-Type: application/json; charset=UTF-8
Content-Length: 248

{
"id":1345,
"name":"DependencyName",
"version":"1.0",
"permissions":"0755"
}
```

## Deploy Dependency

An application can deploy a Dependency to an account to Swift by issuing an HTTP PUT request.
### Request

#### URL structure
The URL that represents the dependency data resource. The URL is
**/filters/dependencies/:account/deploy/:dependency_id/**

#### Method
PUT

#### Request Headers

The request header includes the following information:

FIELD |  DESCRIPTION
--- | ---
**X-Auth-Token** | Token to authenticate to OpenStack Swift as an **Admin**

#### HTTP Request Example

```
Content-Type: application/json
PUT /filters/dependencies/4f0279da74ef4584a29dc72c835fe2c9/deploy/3

```

## Undeploy Dependency

An application can undeploy the Dependency of an account from Swift by issuing an HTTP PUT request.

### Request

#### URL structure
The URL that represents the dependency data resource. The URL is
**/filters/dependencies/:account/undeploy/:dependency_id/**

#### Method
PUT

#### Request Headers

The request header includes the following information:

FIELD |  DESCRIPTION
--- | ---
**X-Auth-Token** | Token to authenticate to OpenStack Swift as an **Admin**

#### HTTP Request Example

```json
Content-Type: application/json
POST /filters/dependencies/4f0279da74ef4584a29dc72c835fe2c9/undeploy/3

```

## List deployed Dependencies of an Account

An application can list all the deployed Dependencies of an account to Swift by issuing an HTTP GET request.

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
**/filters/dependencies/:account/deploy/**

#### Method
GET

#### HTTP Request Example

```json
Content-Length: 294
Content-Type: application/json
GET /filters/dependencies/123/deploy/

```
