SDS Controller API Specification - Swift
===========================================
**Table of Contents**

- [Error handling](#error-handling)
- [Authentication](#authentication)
- [Swift](#storlets)
  - [Tenants](#tenants)

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

#Swift

## List tenants

An application can ask for tenant list by issuing an HTTP GET request.

### Request

#### URL structure
The URL that represents the tenant list resource is
**/swift/tenants.**

#### Method
GET

#### HTTP Request Example

```
Content-Type: application/json
Content-Length: nnn
X-Auth-Token: sdsa23123dsae14342q
GET /swift/tenants
```

### Response

#### Response example

```json

Response <200>
{
  "tenants_links": [],
  "tenants": [
    {
      "description": "Service Tenant",
      "enabled": true,
      "id": "4f0279da74ef4584a29dc72c835fe2c9",
      "name": "service"
    },
    {
      "description": "The storlets management tenant",
      "enabled": true,
      "id": "c357bdff772b4c31883e51fe93c93ac6",
      "name": "storlet_management"
    },
    {
      "description": "Admin Tenant",
      "enabled": true,
      "id": "f29b760ad46447db99ea11f7afc0ed9f",
      "name": "admin"
    }
  ]
}
```
## Locality

An application can ask for the location of specific account/container/object by issuing an HTTP GET request.

### Request

#### URL structure
The URL that represents the locality resource is
**/swift/locality/:account/:container/:swift_object.**
**Note:** Minimum it's mandatory enter the account. However the container and swift_object
is optional.

#### Method
GET

#### HTTP Request Example

```
Content-Type: application/json
Content-Length: 180
GET /swift/locality/AUTH_151542dfdsa541asd455fasf1/test1/file.txt
```

### Response

#### Response example

```json

Response <200>
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
