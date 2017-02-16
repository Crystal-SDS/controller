===============================
Authentication & Error handling
===============================

Authentication
--------------

After successfully receiving the credentials from keystone, it is necessary that all API calls will be authenticated.
To authenticate the calls, it needs to add the header explained in the next table:

+------------------+------------------------------------------------------------------------+
| OAuth PARAMETER  |  DESCRIPTION                                                           |
+==================+========================================================================+
| **X-Auth-Token** | Admin token obtained after a successful authentication in keystone.    |
+------------------+------------------------------------------------------------------------+

Error handling
--------------

Errors are returned using standard HTTP error code syntax.

Any additional info is included in the body of the return call, JSON-formatted.

+---------+----------------------------------------------------------------------------------------------------------------+
|  CODE   |  DESCRIPTION                                                                                                   |
+=========+================================================================================================================+
| **400** | Bad input parameter. Error message should indicate which one and why.                                          |
+---------+----------------------------------------------------------------------------------------------------------------+
| **401** | Authorization required. The presented credentials, if any, were not sufficient to access the folder resource.  |
|         | Returned if an application attempts to use an access token after it has expired.                               |
+---------+----------------------------------------------------------------------------------------------------------------+
| **403** | Forbidden. The requester does not have permission to access the specified resource.                            |
+---------+----------------------------------------------------------------------------------------------------------------+
| **404** | File or folder not found at the specified path.                                                                |
+---------+----------------------------------------------------------------------------------------------------------------+
| **405** | Request method not expected (generally should be GET or POST).                                                 |
+---------+----------------------------------------------------------------------------------------------------------------+
| **5xx** | Server error                                                                                                   |
+---------+----------------------------------------------------------------------------------------------------------------+

