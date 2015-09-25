SDS Controller API Specification - Storlets
===========================================
**Table of Contents**

- [Error handling](#error-handling)
- [Authentication](#authentication)
- [Storlets](#storlets)
  - [Create a Storlet](#create-a-storlet)
  - [Upload a Storlet data](#upload-a-storlet-data)
  - [Delete a Storlet](#delete-a-storlet)
  - [Get Storlet metadata](#get-storlet-metadata)
  - [List Storlets](#list-storlets)
  - [Update Storlet metadata](#update-storlet-metadata)
  - [Deploy a Storlet](#deploy-a-storlet)
  - [Undeploy a Storlet](#undeploy-a-storlet)
  - [List deployed Storlets of an account](#list-deployed-storlets-of-an-account)
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

#Storlets

## Create a Storlet

An application can create a Storlet by issuing an HTTP POST request. The application needs to provide the Storlet metadata like json format. The binary file will be uploaded after this call, first it must upload the metadata fields.

### Request

#### URL structure
The URL that represents the storlet data resource. The URL is
**/storlets.**

#### Method
POST

#### Request Query arguments
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**name** | The name of the storlet to be created.
**language** |Currently must be 'java'
**interface_version** | Currently we have a single version '1.0'
**dependency** | A comma separated list of dependencies. Default: “ ”
**object_metadata** | Currently, not in use, but must appear. Use the value 'no'
**main** | The name of the class that implements the IStorlet API. In our case: 'com.ibm.storlet.identity.IdentityStorlet'

#### HTTP Request Example

```
POST /storlets
```

### Response

#### Response example

```json

Response <201>
{
"id":1345,
"name":"StorletName",
"language":"Java",
"interface_version":"1.0",
"dependency":"’’",
"object_metadata":"no",
"main":"com.urv.storlet.uonetrace.UOneTraceStorlet",
"created_at":"2013-03-08 10:36:41.997",
"deployed":"false"
}
```
## Upload a Storlet data

An application can upload a Storlet data by issuing an HTTP PUT request. The application needs to provide the Storlet data like a binary file in the body content of the request.

### Request

#### URL structure
The URL that represents the storlet data resource. The URL is
**/storlets/:storlet_id/data**.

#### Method
PUT

#### HTTP Request Example

```
POST /storlets/:storlet_id/data

<binary file>
```

## Delete a Storlet

An application can delete a Storlet by issuing an HTTP DELETE request. This call delete the Storlet from Swift and SDS Controller.

### Request

#### URL structure
The URL that represents the storlet data resource. The URL is
**/storlets/:storlet_id.**

#### Method
DELETE

#### HTTP Request Example

```
DELETE /storlets/:storlet_id

```

## Get Storlet metadata

An application can ask for the Storlet metadata by issuing an HTTP GET request.


### Request

#### URL structure
The URL that represents the storlet data resource. The URL is
**/storlets/:storlet_id**

#### Method
GET

#### HTTP Request Example

```
GET /storlets/:storlet_id
```
### Response

#### Response example

```json

HTTP/1.1 200 OK
Content-Type: application/json; charset=UTF-8
Content-Length: 248

{
"id":1345,
"name":"StorletName",
"language":"Java",
"interface_version":"1.0",
"dependency":"’’",
"object_metadata":"no",
"main":"com.urv.storlet.uonetrace.UOneTraceStorlet",
"created_at":"2013-03-08 10:36:41.997",
"deployed":"true"
}


```

## List Storlets

An application can list the Storlets by issuing an HTTP GET request.

### Request

#### URL structure
The URL that represents the storlet data resource. The URL is
**/sotrlets**

#### Method
GET

#### HTTP Request Example

```
GET /storlets

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
"name":"StorletName",
"language":"Java",
"interface_version":"1.0",
"dependency":"’’",
"object_metadata":"no",
"main":"com.urv.storlet.uonetrace.UOneTraceStorlet",
"created_at":"2013-03-08 10:36:41.997",
"deployed":"true"
},{
"id":1345,
"name":"StorletName",
"language":"Java",
"interface_version":"1.0",
"dependency":"’’",
"object_metadata":"no",
"main":"com.urv.storlet.uonetrace.UOneTraceStorlet",
"created_at":"2013-03-08 10:36:41.997",
"deployed":"true"
},{
"id":1345,
"name":"StorletName",
"language":"Java",
"interface_version":"1.0",
"dependency":"’’",
"object_metadata":"no",
"main":"com.urv.storlet.uonetrace.UOneTraceStorlet",
"created_at":"2013-03-08 10:36:41.997",
"deployed":"true"
}
]

```
## Update Storlet metadata

An application can update the Storlet metadata by issuing an HTTP PUT request.

### Request

#### URL structure
The URL that represents the storlet data resource. The URL is
 **/storlets/:storlet_id**.

#### Method
PUT

#### Request Body
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**name** | The name of the storlet to be created.
**language** |Currently must be 'java'
**interface_version** | Currently we have a single version '1.0'
**dependency** | A comma separated list of dependencies. Default: “ ”
**object_metadata** | Currently, not in use, but must appear. Use the value 'no'
**main** | The name of the class that implements the IStorlet API. In our case: 'com.ibm.storlet.identity.IdentityStorlet'

#### HTTP Request Example

```json

PUT /file/32565632156

Content-Length: 294
Content-Type: application/json

{
"name":"StorletName",
"language":"Java",
"interface_version":"1.0",
"dependency":"’’",
"object_metadata":"no",
"main":"com.urv.storlet.uonetrace.UOneTraceStorlet",
}

```
### Response

#### Response example

```json

HTTP/1.1 200 OK
Content-Type: application/json; charset=UTF-8
Content-Length: 248

{
"name":"StorletName",
"language":"Java",
"interface_version":"1.0",
"dependency":"’’",
"object_metadata":"no",
"main":"com.urv.storlet.uonetrace.UOneTraceStorlet",
}

```

## Deploy a Storlet

An application can deploy the Storlet to Swift by issuing an HTTP PUT request.

### Request

#### URL structure
The URL that represents the storlet data resource. The URL is
**/storlets/:account/deploy/:storlet_id/**

#### Method
PUT

#### Request Body
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**params** | The parameters needed by the storlet execution. These parameters are codified as query string. 


#### HTTP Request Example

```json
Content-Type: application/json
PUT storlets/4f0279da74ef4584a29dc72c835fe2c9/deploy/3

{
"params":"select=user_id",
}
```

### Response

#### Response example

```json

HTTP/1.1 201 Created

```
## Undeploy Storlet

An application can undeploy the Storlet of an account from Swift by issuing an HTTP PUT request.

### Request

#### URL structure
The URL that represents the storlet data resource. The URL is
**/storlets/:account/undeploy/:dependency_id/**

#### Method
PUT

#### HTTP Request Example

```json
Content-Type: application/json
POST /storlets/4f0279da74ef4584a29dc72c835fe2c9/undeploy/3

```

## List deployed Storlets of an Account

An application can list all the deployed Storlets of an account to Swift by issuing an HTTP GET request.

### Request

#### URL structure
The URL that represents the storlet data resource. The URL is
**/storlets/:account/deploy/**

#### Method
GET

#### HTTP Request Example

```json
Content-Length: 294
Content-Type: application/json
GET /storlets/123/deploy/

```

# Dependencies
## Create a Dependency

An application can create a Dependency by issuing an HTTP POST request. The application needs to provide the Dependency metadata like json format. The binary file will be uploaded after this call, first it must upload the metadata fields.

### Request

#### URL structure
The URL that represents the storlet data resource. The URL is
**/storlets/dependencies.**
#### Method
POST

#### Request Body
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**name** | The name of the dependency to be created. It is a unique field.
**version** | While the engine currently does not parse this header, it must appear.
**permissions** | An optional metadata field, where the user can state the permissions given to the dependency when it is copied to the Linux container. This is helpful for binary dependencies invoked by the storlet. For a binary dependency once can specify: '0755'

#### HTTP Request Example

```
POST /storlets/dependencies

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
"permissions":"0755",
"created_at":"2013-03-08 10:36:41.997",
"deployed":"False"
}

```

## Upload a Dependency

An application can upload a Dependency data by issuing an HTTP PUT request. The application needs to provide the Dependency data like a binary file in the body content of the request.

### Request

#### URL structure
The URL that represents the storlet data resource. The URL is
**/storlets/dependencies/:dependency_id/data.**

#### Method
PUT

#### HTTP Request Example

```
POST /storlets/dependencies/:dependency_id/data

<binary file>
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

The URL that represents the storlet data resource. The URL is
**/storlets/dependencies/:storlet_id.**

#### Method
DELETE


#### HTTP Request Example

```
DELETE /storlets/dependencies/:dependency_id
```

## Get Dependency metadata

An application can ask for the Dependency metadata by issuing an HTTP GET request.

### Request

#### URL structure

The URL that represents the storlet data resource. The URL is
**/storlets/dependencies/:storlet_id**

#### Method
GET

#### HTTP Request Example

```
GET /storlets/dependencies/:dependency_id
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
"permissions":"0755",
"created_at":"2013-03-08 10:36:41.997",
"deployed":"False"
}
```

## List Dependencies

An application can list the Dependencies by issuing an HTTP GET request.

### Request

#### URL structure

The URL that represents the storlet data resource. The URL is
**/sotrlets/dependencies**

#### Method
GET

#### HTTP Request Example

```
Content-Type: application/json; charset=UTF-8
GET /storlets

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
"permissions":"0755",
"created_at":"2013-03-08 10:36:41.997",
"deployed":"False"
},{
"id":1345,
"name":"DependencyName",
"version":"1.0",
"permissions":"0755",
"created_at":"2013-03-08 10:36:41.997",
"deployed":"False"
},{
"id":1345,
"name":"DependencyName",
"version":"1.0",
"permissions":"0755",
"created_at":"2013-03-08 10:36:41.997",
"deployed":"False"
}
]
```

## Update Dependency metadata

An application can update the Dependency metadata by issuing an HTTP PUT request.

### Request

#### URL structure

The URL that represents the dependency data resource. The URL is
**/storlets/dependencies/:dependency_id**


#### Method
PUT

#### Request Query arguments
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**name** | The name of the dependency to be created. It is a unique field.
**version** | While the engine currently does not parse this header, it must appear.
**permissions** | An optional metadata field, where the user can state the permissions given to the dependency when it is copied to the Linux container. This is helpful for binary dependencies invoked by the storlet. For a binary dependency once can specify: '0755'

#### HTTP Request Example
```json
PUT /storlets/dependencies/123
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
"permissions":"0755",
"created_at":"2013-03-08 10:36:41.997",
"deployed":"False"
}
```

## Deploy Dependency

An application can deploy a Dependency to an account to Swift by issuing an HTTP PUT request.

### Request

#### URL structure
The URL that represents the dependency data resource. The URL is
**/storlets/dependencies/:account/deploy/:dependency_id/**

#### Method
PUT

#### HTTP Request Example

```
Content-Type: application/json
PUT /storlets/dependencies/4f0279da74ef4584a29dc72c835fe2c9/deploy/3

```

## Undeploy Dependency

An application can undeploy the Dependency of an account from Swift by issuing an HTTP PUT request.

### Request

#### URL structure
The URL that represents the dependency data resource. The URL is
**/storlets/dependencies/:account/undeploy/:dependency_id/**

#### Method
PUT

#### HTTP Request Example

```json
Content-Type: application/json
POST /storlets/dependencies/4f0279da74ef4584a29dc72c835fe2c9/undeploy/3

```

## List deployed Dependencies of an Account

An application can list all the deployed Dependencies of an account to Swift by issuing an HTTP GET request.

### Request

#### URL structure
The URL that represents the storlet data resource. The URL is
**/storlets/dependencies/:account/deploy/**

#### Method
GET

#### HTTP Request Example

```json
Content-Length: 294
Content-Type: application/json
GET /storlets/dependencies/123/deploy/

```
