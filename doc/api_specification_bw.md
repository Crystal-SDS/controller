SDS Controller API Specification - BW Differentiation
=====================================================
**Table of Contents**

- [Error handling](#error-handling)
- [BW info](#bw-info)
  - [Get BW info about all accounts](#get-bw-info-about-all-accounts)
  - [Get BW info about an account](#get-bw-info-about-an-account)
- [Clear BW](#clear-bw)
  - [Clear all the BW assignations for all accounts and policies](#clear-all-the-bw-assignations-for-all-accounts-and-policies)
  - [Clear all the BW assignations entries for the selected account](#clears-all-the-bw-assignations-entries-for-the-selected-account)
  - [Clear all the BW assignations entries for the selected account and policy](#clears-all-the-bw-assignations-entries-for-the-selected-account-and-policy)
- [Update BW](#update-bw)
  - [Assign the specified bw to all the policies of the selected account](#assigns-the-specified-bw-to-all-the-policies-of-the-selected-account)
  - [Assign the specified bw to the selected account and policy](#assign-the-specified-bw-to-the-selected-account-and-policy)

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

# BW info

## Get BW info about all accounts

An application can return all the bw information about all accounts by issuing an HTTP GET request.

### Request
#### URL structure
The URL that represents the bw information about all accounts. The URL is **/bw/**

#### Method
GET

#### HTTP Request Example
```
GET /bw/
```

### Response

#### Response example

```json

HTTP/1.1 200 OK

{
"127.0.0.1:6010": {
"AUTH_test": {
"gold": 20,
"silver": 10
},
"AUTH_test2": {
"silver": 25
}
},
"127.0.0.1:6020": {
"AUTH_test": {
"gold": 20,
"silver": 10
},
"AUTH_test2": {
"silver": 25
}
}
}
```

## Get BW info about an account

An application can return all the bw information about an account by issuing an HTTP GET request.

### Request
#### URL structure
The URL that represents the bw information about an account. The URL is **/bw/:account_id**

#### Method
GET

#### HTTP Request Example
```
GET /bw/AUTH_01234567890123456789
```

### Response

#### Response example

```json

HTTP/1.1 200 OK

{
"AUTH_01234567890123456789": {
"gold": 20,
"silver": 10
}
}
```

# Clear BW

## Clear all the BW assignations for all accounts and policies

An application can clear all the BW assignations for all accounts and policies by issuing an HTTP GET request.

### Request
#### URL structure
The URL to clear all the BW assignations for all accounts and policies. The URL is **/bw/clear/**

#### Method
PUT

#### HTTP Request Example
```
PUT /bw/clear/
```

### Response

#### Response example

```json

HTTP/1.1 200 OK

```

## Clear all the BW assignations entries for the selected account

An application can clear all the BW assignations entries for the selected account by issuing an HTTP GET request.

### Request
#### URL structure
The URL to clear all the BW assignations entries for the selected account. The URL is **/bw/clear/:account_id**

#### Method
PUT

#### HTTP Request Example
```
PUT /bw/clear/AUTH_01234567890123456789
```

### Response

#### Response example

```json

HTTP/1.1 200 OK

```

## Clear all the BW assignations entries for the selected account and policy

An application can clear all the BW aassignations entries for the selected account and policy by issuing an HTTP GET request.

### Request
#### URL structure
The URL to clear all the BW assignations entries for the selected account and policy. The URL is **/bw/clear/account_id/policy_id**

#### Method
PUT

#### HTTP Request Example
```
PUT /bw/clear/AUTH_01234567890123456789/silver
```

### Response

#### Response example

```json

HTTP/1.1 200 OK

```

# Update BW

## Assign the specified bw to all the policies of the selected account

An application can assign the specified bw to all the policies of the selected account by issuing an HTTP PUT request.

### Request
#### URL structure
The URL to assign the specified bw to all the policies of the selected account. The URL is **/bw/account_id/bw_value**

#### Method
PUT

#### HTTP Request Example
```
PUT /bw/AUTH_01234567890123456789/10
```

### Response

#### Response example

```json

HTTP/1.1 200 OK

```

## Assign the specified bw to the selected account and policy

An application can assign the specified bw to the selected account and policy by issuing an HTTP PUT request.

### Request
#### URL structure
The URL to assign the specified bw to the selected account and policy. The URL is **/bw/account_id/policy_id/bw_value**

#### Method
PUT

#### HTTP Request Example
```
PUT /bw/AUTH_01234567890123456789/silver/10
```

### Response

#### Response example

```json

HTTP/1.1 200 OK

```
