Crystal Controller API Specification - Filters
==============================================
**Table of Contents**

- [Filters](#filters)
  - [List Filters](#list-filters)
  - [Create a Filter](#create-a-filter)
  - [Upload a Filter data](#upload-a-filter-data)
  - [Delete a Filter](#delete-a-filter)
  - [Get Filter metadata](#get-filter-metadata)
  - [Update Filter metadata](#update-filter-metadata)
  - [Deploy a Filter](#deploy-a-filter)
  - [Undeploy a Filter](#undeploy-a-filter)
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

#Filters

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

[{
"id":"1",
"filter_name": "compression-1.0.jar"
"filter_type":"storlet",
"main":"com.example.StorletCompression",
"is_pre_put":"False",
"is_post_put":"False",
"is_pre_get":"False",
"is_post_get":"False",
"execution_server":"proxy",
"execution_server_reverse":"proxy",
"interface_version":"1.0",
"object_metadata":"",
"dependencies":"",
"has_reverse":"False",
},
{
...
}]
```

## Create a filter

An application can create a filter by issuing an HTTP POST request. The application needs to provide the filter metadata in json format. The binary file will be uploaded after this call, first it must upload the metadata fields.

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
**/filters**

#### Method
POST

#### Request Query arguments
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**filter_type** | The type of filter. Supported values: "storlet", "native" or "global"
**interface_version** | Currently we have a single version "1.0"
**dependencies** | A comma separated list of dependencies. Default: “ ”
**object_metadata** | Currently, not in use, but must appear. Use an empty value ""
**main** | The name of the class that implements the IStorlet API.
**is_pre_put** | Boolean to indicate that the filter will be executed before put requests reach the storage. 
**is_post_put** | Boolean to indicate that the filter will be executed after put requests reach the storage.
**is_pre_get** | Boolean to indicate that the filter will be executed before get requests reach the storage.
**is_post_get** | Boolean to indicate that the filter will be executed after get requests reach the storage. 
**has_reverse** | Boolean to indicate whether the filter has a reverse action, like compression/decompression.
**execution_server** | The execution server for this filter: "proxy" or "object" 
**execution_server_reverse** | The reverse execution server for this filter: "proxy" or "object"
**execution_order** | This parameter can only be sent if filter_type is "global". An integer indicating the execution order of global filters. 
**enabled** | This parameter can only be sent if filter_type is "global". A boolean to indicate if the filter is enabled.

#### HTTP Request Example

```
POST /filters

{
"filter_type": "storlet", 
"interface_version": "1.0", 
"dependencies": "",
"object_metadata": "", 
"main": "com.example.StorletMain",
"is_pre_put": "False", 
"is_post_put": "False",
"is_pre_get": "False",
"is_post_get": "False", 
"has_reverse": "False", 
"execution_server": "proxy", 
"execution_server_reverse": "proxy"
}
```

### Response

#### Response example

```json

Response <201>
{
"id":1345,
"filter_type": "storlet", 
"interface_version": "1.0", 
"dependencies": "",
"object_metadata": "", 
"main": "com.example.StorletMain",
"is_pre_put": "False", 
"is_post_put": "False",
"is_pre_get": "False",
"is_post_get": "False", 
"has_reverse": "False", 
"execution_server": "proxy", 
"execution_server_reverse": "proxy"
}
```

## Upload a filter data

An application can upload a filter data by issuing an HTTP PUT request. The application needs to provide the filter data like a QueryDicct with a single key "file" containing the upload file.
**media_type:** `multipart/form-data`

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
**/filters/{filter_id}/data**.

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
PUT /filters/1345/data
"media_type":"multipart/form-data"
{"file":<binary file>} (QueryDict)

```

## Delete a filter

An application can delete a filter by issuing an HTTP DELETE request. This call deletes the filter from SDS Controller store, **BUT** it does not undeploy this filter from OpenStack Swift. Therefore, some users could maintain activated this filter in their account after delete the filter from SDS Controller.

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
**/filters/{filter_id}**

#### Method
DELETE

#### HTTP Request Example

```
DELETE /filters/1345
```

## Get filter metadata

An application can ask for the filter metadata by issuing an HTTP GET request.

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
**/filters/{filter_id}**

#### Method
GET

#### HTTP Request Example

```
GET /filters/1
```
### Response

#### Response example

```json

HTTP/1.1 200 OK

{
"id":"1",
"filter_name": "compression-1.0.jar"
"filter_type":"storlet",
"main":"com.example.StorletCompression",
"is_pre_put":"False",
"is_post_put":"False",
"is_pre_get":"False",
"is_post_get":"False",
"execution_server":"proxy",
"execution_server_reverse":"proxy",
"interface_version":"1.0",
"object_metadata":"",
"dependencies":"",
"has_reverse":"False",
}

```

## Update filter metadata

An application can update the filter metadata by issuing an HTTP PUT request.

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
 **/filters/{filter_id}**

#### Method
PUT

#### Request Body
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**interface_version** | Currently we have a single version "1.0"
**dependencies** | A comma separated list of dependencies. Default: “ ”
**object_metadata** | Currently, not in use, but must appear. Use an empty value ""
**main** | The name of the class that implements the IStorlet API.
**is_pre_put** | Boolean to indicate that the filter will be executed before put requests reach the storage. 
**is_post_put** | Boolean to indicate that the filter will be executed after put requests reach the storage.
**is_pre_get** | Boolean to indicate that the filter will be executed before get requests reach the storage.
**is_post_get** | Boolean to indicate that the filter will be executed after get requests reach the storage. 
**has_reverse** | Boolean to indicate whether the filter has a reverse action, like compression/decompression.
**execution_server** | The execution server for this filter: "proxy" or "object" 
**execution_server_reverse** | The reverse execution server for this filter: "proxy" or "object"
**execution_order** | This parameter can only be sent if filter_type is "global". An integer indicating the execution order of global filters. 
**enabled** | This parameter can only be sent if filter_type is "global". A boolean to indicate if the filter is enabled.

#### HTTP Request Example

```json

PUT filters/1

{
"filter_type": "storlet", 
"interface_version": "1.0", 
"dependencies": "",
"object_metadata": "", 
"main": "com.example.StorletMain",
"is_pre_put": "False", 
"is_post_put": "False",
"is_pre_get": "False",
"is_post_get": "False", 
"has_reverse": "False", 
"execution_server": "proxy", 
"execution_server_reverse": "proxy"
}

```
### Response

#### Response example

```json

HTTP/1.1 200 OK

```

## Deploy a filter

An application can deploy a filter to Swift by issuing an HTTP PUT request. This operation creates a static policy 

### Request

#### URL structure
The URL that represents the deployment of a filter to a project. The URL is
**/filters/{project}/deploy/{filter_id}/**

Similarly, to deploy a filter to a project and a container, the URL is
**/filters/{project}/{container}/deploy/{filter_id}/**

#### Method
PUT

#### Request Body
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**params** | The parameters needed by the filter execution. These parameters are codified as query string.
**object_type** | String. The type of objects the filter will be applied to.
**object_size** | String. The size of objects the filter will be applied to.


#### HTTP Request Example

```json
Content-Type: application/json
PUT /filters/4f0279da74ef4584a29dc72c835fe2c9/deploy/3

{
"params":"select=user_id, type=string",
"object_type":"DOCS",
"object_size":">2000",
}
```

### Response

The response is the id of the new static policy associated with the filter deployment.

#### Response example

```json

HTTP/1.1 201 Created

1
```

## Undeploy a Filter

An application can undeploy the filter from a Swift project by issuing an HTTP PUT request.

### Request

#### URL structure
The URL that represents the filter data resource. The URL is
**/filters/{project}/undeploy/{filter_id}/**

#### Method
PUT

#### HTTP Request Example

```json
Content-Type: application/json
PUT /filters/4f0279da74ef4584a29dc72c835fe2c9/undeploy/3

```

# Dependencies
## Create a Dependency

An application can create a Dependency by issuing an HTTP POST request. The application needs to provide the Dependency metadata like json format. The binary file will be uploaded after this call, first it must upload the metadata fields.

### Request

#### URL structure
The URL that represents the filter dependencies resource. The URL is
**/filters/dependencies.**
#### Method
POST

#### Request Body
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**name** | The name of the dependency to be created. It is a unique field.
**version** | While the engine currently does not parse this header, it must appear.
**permissions** | An optional metadata field, where the user can state the permissions given to the dependency when it is copied to the Linux container. This is helpful for binary dependencies invoked by the filter. For a binary dependency once can specify: "0755"

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

## Upload a Dependency Data

An application can upload a Dependency data by issuing an HTTP PUT request. The application needs to provide the dependency data like a QueryDict with a single key "file" containing the upload file.
**media_type:** `multipart/form-data`


### Request

#### URL structure
The URL that represents a filter dependency resource. The URL is
**/filters/dependencies/{dependency_id}/data**

#### Method
PUT

#### HTTP Request Example

```
PUT /filters/dependencies/:dependency_id/data
"media_type":"multipart/form-data"

{"file":<binary file>} (QueryDicct)
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

The URL that represents a filter dependency resource. The URL is
**/filters/dependencies/{dependency_id}**

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

The URL that represents a filter dependency resource. The URL is
**/filters/dependencies/{dependency_id}**

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

The URL that represents filter dependencies resource. The URL is
**/filters/dependencies**

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

The URL that represents a filter dependency resource. The URL is
**/filters/dependencies/{dependency_id}**

#### Method
PUT

#### Request Query arguments
JSON input that contains a dictionary with the following keys:

FIELD |  DESCRIPTION
--- | ---
**name** | The name of the dependency to be created. It is a unique field.
**version** | While the engine currently does not parse this header, it must appear.
**permissions** | An optional metadata field, where the user can state the permissions given to the dependency when it is copied to the Linux container. This is helpful for binary dependencies invoked by the filter. For a binary dependency once can specify: "0755"

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
The URL that represents the a filter dependency resource. The URL is
**/filters/dependencies/{project}/deploy/{dependency_id}/**

#### Method
PUT

#### HTTP Request Example

```
PUT /filters/dependencies/4f0279da74ef4584a29dc72c835fe2c9/deploy/3

```

## Undeploy Dependency

An application can undeploy the Dependency of an account from Swift by issuing an HTTP PUT request.

### Request

#### URL structure
The URL that represents the filter dependency data resource. The URL is
**/filters/dependencies/{project}/undeploy/{dependency_id}/**

#### Method
PUT

#### HTTP Request Example

```json
PUT /filters/dependencies/4f0279da74ef4584a29dc72c835fe2c9/undeploy/3

```

## List deployed Dependencies of an Account

An application can list all the deployed Dependencies of an account to Swift by issuing an HTTP GET request.

### Request

#### URL structure
The URL that represents the filter dependencies data resource. The URL is
**/filters/dependencies/{project}/deploy/**

#### Method
GET

#### HTTP Request Example

```json

GET /filters/dependencies/123/deploy/

```
