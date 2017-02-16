==============
Controller API
==============


Workload metrics
================

Add a workload metric
---------------------

An application can registry a metric workload by issuing an HTTP POST request. The application needs to provide the metric workload metadata like json format.

Request
```````

URL structure
	The URL is **/registry/metrics**

Method
	POST

Request Query arguments
    JSON input that contains a dictionary with the following keys:

    +-----------------------------+----------------------------------------------------------------------------------------------+
    | FIELD                       | DESCRIPTION                                                                                  |
    +=============================+==============================================================================================+
    | **name**                    | The name is the keyword to be used in condition clauses of storage policy definitions.       |
    |                             | Workload metric names should be unique and self-descriptive to ease the design of storage    |
    |                             | policies.                                                                                    |
    +-----------------------------+----------------------------------------------------------------------------------------------+
    | **network_location**        | This requires the metadata information of a workload metric to provide the network location  |
    |                             | to reach the process and obtain the computed metric.                                         |
    +-----------------------------+----------------------------------------------------------------------------------------------+
    | **type**                    | Workload metric’s metadata should define the type of metric produces, such as integer or a   |
    |                             | boolean, to enable the DSL syntax checker to infer if values in condition clauses belong to  |
    |                             | the appropriate type.                                                                        |
    +-----------------------------+----------------------------------------------------------------------------------------------+

HTTP Request Example

    .. code-block:: json

        POST /registry/metrics

        {
        "name": "put_active_requests",
        "network_location": "tcp://127.0.0.1:6899/registry.policies.metrics.swift_metric/SwiftMetric/put_active_requests",
        "type": "integer"
        }

Response
````````

Response example

    .. code-block:: json

        Response <201>
        TODO

Get all workload metrics
------------------------

An application can get all the metrics registered by issuing an HTTP GET request.

Request
```````

URL structure
    The URL is **/registry/metrics**

Method
	GET

HTTP Request Example

    .. code-block:: json

        GET /registry/metrics

Response
````````

Response example

    .. code-block:: json

        Response <201>
        [{
        "name": "put_active_requests",
        "network_location": "tcp://127.0.0.1:6899/registry.policies.metrics.swift_metric/SwiftMetric/put_active_requests",
        "type": "integer"
        },{
        "name": "get_active_requests",
        "network_location": "tcp://127.0.0.1:6899/registry.policies.metrics.swift_metric/SwiftMetric/get_active_requests",
        "type": "integer"
        }]

Update a workload metric
------------------------

An application can update the metadata of a workload metric by issuing an HTTP PUT request.

Request
```````

URL structure
	The URL is **/registry/metrics/{metric_name}**

Method
	PUT

HTTP Request Example

    .. code-block:: json

        PUT /registry/metrics/put_active_requests
        {
          "network_location": "tcp://192.168.1.5:6899/registry.policies.metrics.swift_metric/SwiftMetric/put_active_requests"
        }

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 201 CREATED

Get metric metadata
-------------------

An application can ask for a workload metric metadata by issuing an HTTP GET request.

Request
```````

URL structure
	The URL is **/registry/metrics/{metric_name}**

Method
	GET

HTTP Request Example

    .. code-block:: json

        GET /registry/metrics/put_active_requests

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 200 OK

        {
        "name": "put_active_requests",
        "network_location": "tcp://127.0.0.1:6899/registry.policies.metrics.swift_metric/SwiftMetric/put_active_requests",
        "type": "integer"
        }

Delete a workload metric
------------------------

An application can delete a workload metric by issuing an HTTP DELETE request.

Request
```````

URL structure
	The URL is **/registry/metrics/{metric_name}**

Method
	DELETE

HTTP Request Example

    .. code-block:: json

        DELETE /registry/metrics/put_active_requests

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 204 NO CONTENT

Filters
=======

Register a filter
-----------------

An application can register a filter by issuing an HTTP POST request. The application needs to provide the filter metadata in json format.

Request
```````

URL structure
	The URL is **/registry/filters**

Method
	POST

Request Query arguments
    JSON input that contains a dictionary with the following keys:

    +----------------------+----------------------------------------------------------------------------------------------+
    | FIELD                | DESCRIPTION                                                                                  |
    +======================+==============================================================================================+
    | **name**             | Filter names should be unique and self-descriptive to ease the design of storage policies.   |
    +----------------------+----------------------------------------------------------------------------------------------+
    | **identifier**       | The identifier of the previously uploaded filter.                                            |
    +----------------------+----------------------------------------------------------------------------------------------+
    | **activation_url**   | Different filter types may have distinct calls from the SDS Controller API viewpoint,        |
    |                      | we need to provide the base URL to be used to trigger the filter activation.                 |
    +----------------------+----------------------------------------------------------------------------------------------+
    | **valid_parameters** | Dictionary where the keys are the parameters accepted by the filter, and the values are the  |
    |                      | type (i.e. boolean, integer) of each parameter.                                              |
    +----------------------+----------------------------------------------------------------------------------------------+

HTTP Request Example

    .. code-block:: json

        POST /registry/filters

        {
        "name":"compression",
        "identifier":2,
        "activation_url":"http://sds_controller/filters/1",
        "valid_parameters":{"param1":"bool", "param2":"integer"}
        }

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 201 CREATED

Get all registered filters
--------------------------

An application can get all registered filters by issuing an HTTP PUT request.

Request
```````

URL structure
	The URL is **/registry/filters**


Method
	GET

HTTP Request Example

    .. code-block:: json

        GET /registry/filters

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 200 OK

        [{
          "name":"compression",
          "identifier":2,
          "activation_url":"http://sds_controller/filters/1",
          "valid_parameters":{"param1":"bool", "param2":"integer"}
        },{
          "name":"compression_gzip",
          "identifier":2,
          "activation_url":"http://sds_controller/filters/1",
          "valid_parameters":{"param1":"bool", "param2":"integer"}
        }]

Update a registered filter
--------------------------

An application can update the metadata of a registered filter by issuing an HTTP PUT request.

Request
```````

URL structure
	The URL is **/registry/filters/{filter_name}**

Method
	PUT

HTTP Request Example

    .. code-block:: json

        PUT /registry/filters/compression

        {
        "activation_url":"http://sds_controller/filters/2"
        }

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 201 CREATED

Get registered filter metadata
------------------------------

An application can ask for a filter metadata by issuing an HTTP GET request.

Request
```````

URL structure
	The URL is **/registry/filters/{filter_name}**

Method
	GET

HTTP Request Example

    .. code-block:: json

        GET /registry/filters/compression

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 200 OK

        {
          "name":"compression",
          "identifier":2,
          "activation_url":"http://sds_controller/filters/2",
          "valid_parameters":{"param1":"bool", "param2":"integer"}
        }

Delete a registered filter
--------------------------

An application can delete a registered filter by issuing an HTTP DELETE request.

Request
```````

URL structure
	The URL is **/registry/filters/{filter_name}**

Method
	DELETE

HTTP Request Example

    .. code-block:: json

        DELETE /registry/filters/compress

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 204 NO CONTENT


Projects group
==============

Add a projects group
--------------------

An application can registry a projects group by issuing an HTTP POST request. The application needs to provide the project identifiers in a json array.

Request
```````

URL structure
	The URL is **/registry/gtenants**

Method
	POST

Request Query arguments
    JSON input that contains an array of project identifiers.

HTTP Request Example

    .. code-block:: json

        POST /registry/gtenants

        [
        "111456789abcdef",
        "222456789abcdef",
        "333456789abcdef",
        ]

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 201 CREATED

Get all projects groups
-----------------------

An application can get all projects groups registered by issuing an HTTP GET request.

Request
```````

URL structure
	The URL is **/registry/gtenants**


Method
	GET

HTTP Request Example

    .. code-block:: json

        GET /registry/gtenants

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 200 OK
        {
          "2": [
            "000456789abcdef",
            "888456789abcdef",
            "999456789abcdef"
          ],
          "3": [
            "111456789abcdef",
            "222456789abcdef",
            "333456789abcdef"
          ]
        }

Get projects of a group
-----------------------

An application can get all tenants of a group registered by issuing an HTTP GET request.

Request
```````

URL structure
	The URL is **/registry/gtenants/{gtenant_id}**


Method
	GET

HTTP Request Example

    .. code-block:: json

        GET /registry/gtenants/3

Response
````````

Response example

    .. code-block:: json

        Response <201>
        [
            "111456789abcdef",
            "222456789abcdef",
            "333456789abcdef"
        ]

Update members of a projects group
----------------------------------

An application can modify the members of a group by issuing an HTTP PUT request.

Request
```````

URL structure
	The URL is **/registry/gtenants/{gtenant_id}**

Method
	PUT

HTTP Request Example

    .. code-block:: json

        PUT /registry/gtenants/2

        [
        "111456789abcdef",
        "222456789abcdef"
        ]

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 201 CREATED

Delete a projects group
-----------------------

An application can delete a projects group by issuing an HTTP DELETE request.

Request
```````

URL structure
	The URL is **/registry/gtenants/{gtenant_id}**

Method
	DELETE

HTTP Request Example

    .. code-block:: json

        DELETE /registry/gtenants/2

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 204 NO CONTENT

Delete a member of a projects group
-----------------------------------

An application can delete a member of a projects group by issuing an HTTP DELETE request.

Request
```````

URL structure
	The URL is **/registry/gtenants/{gtenant_id}/tenants/{project_id}**

Method
	DELETE

HTTP Request Example

    .. code-block:: json

        DELETE /registry/gtenants/2/tenants/111456789abcdef

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 204 NO CONTENT

Object type
===========

Create an object type
---------------------

An application can registry an object type by issuing an HTTP POST request. The application needs to provide the json dictionary with the name of the object type and the file extensions.

Request
```````

URL structure
	The URL is **/registry/object_type**

Method
	POST

Request Query arguments
    JSON input that contains a dictionary with the following keys:

    +----------------------+----------------------------------------------------------------------------------------------+
    | FIELD                | DESCRIPTION                                                                                  |
    +======================+==============================================================================================+
    | **name**             | The name of the object type.                                                                 |
    +----------------------+----------------------------------------------------------------------------------------------+
    | **types_list**       | An array of file extensions.                                                                 |
    +----------------------+----------------------------------------------------------------------------------------------+

HTTP Request Example

    .. code-block:: json

        POST /registry/object_type

        {
        "name": "DOCS",
        "types_list": ["doc","docx","xls","txt"]
        }

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 201 CREATED

Get all object types
--------------------

An application can obtain all registered object types by issuing an HTTP GET request.

Request
```````

URL structure
	The URL is **/registry/object_type**

Method
	GET

HTTP Request Example

    .. code-block:: json

        GET /registry/object_type

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 200 OK

        [
        {
        "name": "DOCS",
        "types_list": ["doc","docx","xls","txt"]
        },
        {
        "name": "PICS",
        "types_list": ["jpg","jpeg","png","gif"]
        }
        ]

Get extensions of an object type
--------------------------------

An application can obtain the extensions list of a particular object type by issuing an HTTP GET request.

Request
```````

URL structure
	The URL is **/registry/object_type/{object_type_name}**

Method
	GET

HTTP Request Example

    .. code-block:: json

        GET /registry/object_type/PICS

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 200 OK

        {
        "name": "PICS",
        "types_list": ["jpg","jpeg","png","gif"]
        }


Update extensions of an object type
-----------------------------------

An application can update an object type by issuing an HTTP PUT request.

Request
```````

URL structure
	The URL is **/registry/object_type/{object_type_name}**

Method
	PUT

Request Query arguments
    JSON input that contains an array of file extensions.

HTTP Request Example

    .. code-block:: json

        PUT /registry/object_type/PICS

        ["jpg","jpeg","png","gif","bmp"]


Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 201 CREATED

Delete an object type
---------------------

An application can delete an object type by issuing an HTTP DELETE request.

Request
```````

URL structure
	The URL is **/registry/object_type/{object_type_name}**

Method
	DELETE

HTTP Request Example

    .. code-block:: json

        DELETE /registry/object_type/PICS

        ["jpg","jpeg","png","gif","bmp"]


Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 200 OK

Metric modules
==============

Upload a metric module
----------------------

An application can upload a metric module by issuing an HTTP POST request. The application needs to provide the metric module data like a QueryDict with a key 'file' containing the upload file and a key 'metadata' containing a JSON object with metric module metadata.
**media_type:** `multipart/form-data`

Request
```````

URL structure
	The URL that represents the metric module data resource. The URL is
**/registry/metric_module/data**

Method
	POST

Request Headers

    The request header includes the following information:

    +----------------------+------------------------------------------------------------------------------------------------------------+
    | FIELD                | DESCRIPTION                                                                                                |
    +======================+============================================================================================================+
    | **X-Auth-Token**     | Token to authenticate to OpenStack Swift as an **Admin**                                                   |
    +----------------------+------------------------------------------------------------------------------------------------------------+
    | **enctype**          | The content type and character encoding of the response. The content type must be **multipart/form-data**. |
    +----------------------+------------------------------------------------------------------------------------------------------------+

    The **metadata** parameter is a JSON object with the following fields:

    +----------------------+------------------------------------------------------------------------------------------------------------+
    | FIELD                | DESCRIPTION                                                                                                |
    +======================+============================================================================================================+
    | **class_name**       | The main class of the metric module to be created.                                                         |
    +----------------------+------------------------------------------------------------------------------------------------------------+
    | **in_flow**          | Boolean indicating whether the metric applies to input flow.                                               |
    +----------------------+------------------------------------------------------------------------------------------------------------+
    | **out_flow**         | Boolean indicating whether the metric applies to output flow.                                              |
    +----------------------+------------------------------------------------------------------------------------------------------------+
    | **execution_server** | 'object' or 'proxy' depending on the server the metric should run on.                                      |
    +----------------------+------------------------------------------------------------------------------------------------------------+
    | **enabled**          | Boolean indicating whether the metric module should be enabled or not.                                     |
    +----------------------+------------------------------------------------------------------------------------------------------------+



HTTP Request Example

    .. code-block:: json

        POST /registry/metric_module/data

        "media_type":"multipart/form-data"
        file=<file get_active_requests.py>
        metadata={
        "class_name": "GetActiveRequests",
        "in_flow": True,
        "out_flow": False,
        "execution_server": "proxy",
        "enabled": True
        }

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 201 CREATED

        {
        "id": 1,
        "metric_name": "get_active_requests",
        "class_name": "GetActiveRequests",
        "in_flow": True,
        "out_flow": False,
        "execution_server": "proxy",
        "enabled": True
        }


Get all metrics modules
-----------------------

An application can get all metric modules by issuing an HTTP GET request.

Request
```````

URL structure
	The URL that represents the metric module data resource. The URL is **/registry/metric_module**

Method
	GET

HTTP Request Example

    .. code-block:: json

        GET /registry/metric_module

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 200 OK

        [
        {
        "id": 1,
        "metric_name": "get_active_requests",
        "class_name": "GetActiveRequests",
        "in_flow": True,
        "out_flow": False,
        "execution_server": "proxy",
        "enabled": True
        },
        {
        "id": 2,
        "metric_name": "get_bw",
        "class_name": "GetBw",
        "in_flow": True,
        "out_flow": False,
        "execution_server": "proxy",
        "enabled": True
        }
        ]

Get a metric module
-------------------

An application can get a metric module info by issuing an HTTP GET request.

Request
```````

URL structure
	The URL that represents the metric module data resource. The URL is **/registry/metric_module/{metric_module_id}**

Method
	GET

HTTP Request Example

    .. code-block:: json

        GET /registry/metric_module/1

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 200 OK

        {
        "id": 1,
        "metric_name": "get_active_requests",
        "class_name": "GetActiveRequests",
        "in_flow": True,
        "out_flow": False,
        "execution_server": "proxy",
        "enabled": True
        }

Update a metric module
----------------------

An application can update a metric module metadata by issuing an HTTP PUT request.

Request
```````

URL structure
	The URL that represents the metric module data resource. The URL is **/registry/metric_module/{metric_module_id}**

Method
	PUT

HTTP Request Example

    .. code-block:: json

        PUT /registry/metric_module/1

        {
        "class_name": "GetActiveRequests",
        "in_flow": True,
        "out_flow": False,
        "execution_server": "proxy",
        "enabled": False
        }

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 200 OK

Delete a metric module
----------------------

An application can delete a metric module metadata by issuing an HTTP DELETE request.

Request
```````

URL structure
	The URL that represents the metric module data resource. The URL is **/registry/metric_module/{metric_module_id}**

Method
	DELETE

HTTP Request Example

    .. code-block:: json

        DELETE /registry/metric_module/1

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 204 NO CONTENT

DSL Policies
============

List all static policies
------------------------

An application can get all static policies sorted by execution order by issuing an HTTP GET request.

Request
```````

URL structure
	The URL that represents the static policy resource. The URL is **/registry/static_policy**

Method
	GET

HTTP Request Example

    .. code-block:: json

        GET /registry/static_policy

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 200 OK

        [
        {
        "id": "1",
        "target_id": "1234567890abcdef",
        "target_name": "tenantA",
        "filter_name": "compression-1.0.jar",
        "object_type": "",
        "object_size": "",
        "execution_server": "proxy",
        "execution_server_reverse": "proxy",
        "execution_order": "1",
        "params": ""
        },
        {
        "id": "2",
        "target_id": "1234567890abcdef",
        "target_name": "tenantA",
        "filter_name": "encryption-1.0.jar",
        "object_type": "",
        "object_size": "",
        "execution_server": "proxy",
        "execution_server_reverse": "proxy",
        "execution_order": "2",
        "params": ""
        },
        ]

Add a static policy
-------------------

An application can add a new static policy by issuing an HTTP POST request.

Request
```````

URL structure
	The URL that represents the static policy resource. The URL is **/registry/static_policy**

Method
	POST /registry/static_policy

Request Body
    The request body is a text/plain input with one or various DSL rules separated by newlines. Refer to :ref:`dsl_grammar` for a detailed explanation of Crystal DSL.

HTTP Request Example

    .. code-block:: json

        Content-Type: text/plain
        POST /registry/static_policy

        FOR TENANT:1234567890abcdef DO SET compression

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 201 CREATED

Get a static policy
-------------------

An application can get all static policies sorted by execution order by issuing an HTTP GET request.

Request
```````

URL structure
	The URL that represents the static policy resource. The URL is **/registry/static_policy/{project_id}:{policy_id}**

Method
	GET

HTTP Request Example

    .. code-block:: json

        GET /registry/static_policy/1234567890abcdef:1

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 200 OK

        {
        "id": "1",
        "target_id": "1234567890abcdef",
        "target_name": "tenantA",
        "filter_name": "compression-1.0.jar",
        "object_type": "",
        "object_size": "",
        "execution_server": "proxy",
        "execution_server_reverse": "proxy",
        "execution_order": "1",
        "params": ""
        }


Update a static policy
----------------------

An application can update the static policy metadata by issuing an HTTP PUT request.

Request
```````

URL structure
	The URL that represents the static policy resource. The URL is **/registry/static_policy/{project_id}:{policy_id}**

Method
	PUT

HTTP Request Example

    In the following example, a put request is issued to change the execution server of the policy to object server:

    .. code-block:: json

        PUT /registry/static_policy/1234567890abcdef:1

        {
        "execution_server": "object",
        "execution_server_reverse": "object"
        }

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 201 CREATED

Delete a static policy
------------------------

An application can delete a static policy by issuing an HTTP DELETE request.

Request
```````

URL structure
	The URL that represents the static policy resource. The URL is **/registry/static_policy/{project_id}:{policy_id}**

Method
	DELETE

HTTP Request Example

    .. code-block:: json

        DELETE /registry/static_policy/1234567890abcdef:1

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 204 NO CONTENT

List all dynamic policies
------------------------

An application can get all dynamic policies by issuing an HTTP GET request.

Request
```````

URL structure
	The URL that represents the dynamic policy resource. The URL is **/registry/dynamic_policy**

Method
	GET

HTTP Request Example

    .. code-block:: json

        GET /registry/dynamic_policy

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 200 OK

        [
        {
        "id": "3",
        "policy": "FOR TENANT:d70b71fc4c02466bb97544bd2c7c0932 DO SET compression",
        "condition": "put_ops<3",
        "transient": True,
        "policy_location": "tcp://127.0.0.1:6899/registry.policies.rules.rule_transient/TransientRule/policy:3",
        "alive": True
        },
        {
        ...
        }
        ]

Add a dynamic policy
--------------------

An application can add a new dynamic policy by issuing an HTTP POST request.

Request
```````

URL structure
	The URL that represents the dynamic policy resource. The URL is **/registry/dynamic_policy**

Method
	POST /registry/dynamic_policy

Request Body
    The request body is a text/plain input with one or various DSL rules separated by newlines. Refer to [Crystal DSL Grammar](/doc/api_dsl.md) for a detailed explanation of Crystal DSL.

HTTP Request Example

    .. code-block:: json

        Content-Type: text/plain
        POST /registry/dynamic_policy

        FOR TENANT:1234567890abcdef WHEN put_ops < 3  DO SET compression

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 201 CREATED

Delete a dynamic policy
-----------------------

An application can delete a dynamic policy by issuing an HTTP DELETE request.

Request
```````

URL structure
	The URL that represents the dynamic policy resource. The URL is **/registry/dynamic_policy/{policy_id}**

Method
	DELETE

HTTP Request Example

    .. code-block:: json

        DELETE /registry/dynamic_policy/3

Response
````````

Response example

    .. code-block:: json

        HTTP/1.1 204 NO CONTENT
