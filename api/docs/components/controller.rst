==========
Controller
==========

The Crystal Controller is the Software-Defined-Storage (SDS) REST API in the IOStack_ architecture.
It is a Django project that implements the REST API needed to handle filters, storlets and policies on top of Openstack Swift object-storage system.
This API also includes a set of python processes who use the `PyActive middleware`_, an Object Oriented implementation of the Actor model.

This part allows to create simple policies using a DSL (integrated in the Crystal Controller API)
and to deploy them as an actor process, who analyze the system data thanks to the monitoring system,
and allows to set or remove filters to tenants depending on the established policy.

.. _IOStack: https://github.com/iostackproject
.. _PyActive middleware: https://github.com/cloudspaces/pyactive