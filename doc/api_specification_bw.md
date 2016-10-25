Crystal Controller API Specification - BW Differentiation
=========================================================
**Table of Contents**

- [SLA info](#sla-info)
  - [Get SLA info about all projects](#get-sla-info-about-all-projects)
  - [Get SLA info about a project and a policy](#get-sla-info-about-a-project-and-a-policy)
  - [Create a SLA for the selected project and policy](#create-a-sla-for-the-selected-project-and-policy)
  - [Edit a SLA for the selected project and policy](#edit-a-sla-for-the-selected-project-and-policy)
  - [Delete a SLA for the selected project and policy](#delete-a-sla-for-the-selected-project-and-policy)

# SLA info

## Get SLA info about all projects

An application can return all the SLA information about all projects by issuing an HTTP GET request.

### Request
#### URL structure
The URL that represents the SLA information about all projects. The URL is **/bw/slas/**

#### Method
GET

#### HTTP Request Example
```
GET /bw/slas/
```

### Response

#### Response example

```json

HTTP/1.1 200 OK

[
{"policy_id": "2",
"project_id": "0123456789abcdef",
"bandwidth": "2000",
"project_name": "tenantA",
"policy_name": "s0y1"},
{"policy_id": "3",
"project_id": "abcdef0123456789",
"bandwidth": "3000",
"project_name": "tenantB",
"policy_name": "s3y4"},
]
```

## Get SLA info about a project and a policy

An application can return all the SLA information about a project and a policy by issuing an HTTP GET request.

### Request
#### URL structure
The URL that represents the SLA information about a project and a policy. The URL is **/bw/sla/{project_id}:{policy_id}**

#### Method
GET

#### HTTP Request Example
```
GET /bw/sla/0123456789abcdef:2
```

### Response

#### Response example

```json

HTTP/1.1 200 OK

{
"policy_id": "2",
"project_id": "0123456789abcdef",
"bandwidth": "2000",
"project_name": "tenantA",
"policy_name": "s0y1"
}
```

## Create a SLA for the selected project and policy

An application can create a SLA for the selected project and policy by issuing an HTTP POST request.

### Request
#### URL structure
The URL to create a SLA for the selected project and policy is **/bw/slas** with a body containing a JSON object.

#### Method
POST

#### HTTP Request Example
```
PUT /bw/slas/
{
"project_id": "0123456789abcdef", 
"policy_id": "4", 
"bandwidth": "4000"
}
```

### Response

#### Response example

```json

HTTP/1.1 201 CREATED

```

## Edit a SLA for the selected project and policy

An application can modify the assigned bandwidth of a project and a policy by issuing an HTTP PUT request.

### Request
#### URL structure
The URL that represents the SLA information about a project and a policy. The URL is **/bw/sla/{project_id}:{policy_id}** with a body containing a JSON object.

#### Method
PUT

#### HTTP Request Example
```
PUT /bw/sla/0123456789abcdef:2
{
"bandwidth": "1000"
}
```

### Response

#### Response example

```json

HTTP/1.1 201 CREATED
```


## Delete a SLA for the selected project and policy

An application can delete the SLA information about a project and a policy by issuing an HTTP DELETE request.

### Request
#### URL structure
The URL that represents the SLA information about a project and a policy. The URL is **/bw/sla/{project_id}:{policy_id}**

#### Method
DELETE

#### HTTP Request Example
```
DELETE /bw/sla/0123456789abcdef:2
```

### Response

#### Response example

```json

HTTP/1.1 204 NO CONTENT
```

