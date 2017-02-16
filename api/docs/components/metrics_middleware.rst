==================
Metric Middleware
==================

Crystal Metric Middleware is a middleware for OpenStack Swift that dynamically manages monitoring metrics.

Crystal Metric Middleware is an extension point of Crystal: new metrics can be added in order to provide more information to the controller.
The github repository includes some `metric samples`_  like the number of GET/PUT operations, the number of active operations,
the bandwidth used or the request performance.

.. _metric samples: https://github.com/Crystal-SDS/metric-middleware/tree/master/metric_samples

The code below is an example of a simple metric that counts GET requests:

    .. code-block:: python

        from crystal_metric_middleware.metrics.abstract_metric import AbstractMetric

        # The metric class inherits from AbstractMetric
        class GetOps(AbstractMetric):

            # This method must be implemented because is the main interception point.
            def execute(self):
                # Setting the type of the metric. The metric internal value is reset when it is
                # published (at periodic intervals)
                self.type = 'stateless'

                # Checking if it's a GET operation and an object request
                if self.method == "GET" and self._is_object_request():
                    # register_metric(key, value) increments by one the current metric (GetOps)
                    # for the current target tenant
                    self.register_metric(self.account, 1)

                return self.response

The code below is an example of a bandwidth metric for GET object requests:

    .. code-block:: python

        class GetBw(AbstractMetric):

            def execute(self):
                self.type = 'stateless'

                if self.method == "GET" and self._is_object_request():
                    # By calling _intercept_get(), all read chunks will enter on_read method
                    self._intercept_get()

                # If the request is intercepted with _intercept_get() it is necessary to return the response
                return self.response

            def on_read(self, chunk):
                # In this case, the metric counts the number of bytes
                mbytes = (len(chunk)/1024.0)/1024
                self.register_metric(self.account, mbytes)

The next example shows a metric that counts active PUT requests:

    .. code-block:: python

        class PutActiveRequests(AbstractMetric):

            def execute(self):
                # The type is stateful: the internal value is never reset
                self.type = 'stateful'

                if self.method == "PUT" and self._is_object_request():
                    self._intercept_put()
                    # Incrementing the metric (a new active PUT request has been intercepted)
                    self.register_metric(self.account, 1)

                return self.request

            def on_finish(self):
                # Decrementing the metric (the PUT request has just finished)
                self.register_metric(self.account, -1)

Metric classes (inheriting from AbstractMetric) must implement the `execute()` method and can implement the optional `on_read()` and `on_finish()` methods.

- `execute()`: This method is the main interception point. If the metric needs access to the data flow or needs to know when the request has finished,
  it has to call `self._intercept_get()` or `self._intercept_put()`.
- `on_read()`: this method is called if the metric has previously called `self._intercept_get()` or `self._intercept_put()`.
  All read chunks will enter this method.
- `on_finish()`: this method is called if the metric has previously called `self._intercept_get()` or `self._intercept_put()`.
  This method is called once the request has been completed.

There are three types of metrics supported:

- `stateless`: the default type. When the metric is published (typically at one second intervals), the internal value is reset to 0.
- `stateful`: when the metric is published, the internal value is not reset. Thus, the value can be incremented/decremented during the next intervals.
  In a previous example, a stateful metric is used to count the active PUT requests: whenever a request is intercepted the metric value is incremented, and when the request finishes the metric value is decremented. At periodic intervals the metric value is published, showing how many concurrent requests are being served at a given instant.
- `force`: this type of metric is published directly after the call to register_metric instead of being published at intervals.

Metric classes must be registered and enabled through `Crystal controller API`_.
A convenient `web dashboard`_ is also available to simplify these API calls.

.. _Crystal controller API: https://github.com/Crystal-SDS/controller/
.. _web dashboard: https://github.com/iostackproject/SDS-dashboard