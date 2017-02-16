================
Crystal Overview
================

Crystal is a transparent, dynamic and open Software-Defined Storage (SDS) system for `OpenStack Swift`_.

.. _OpenStack Swift: http://swift.openstack.org/

As depicted in the figure below, Crystal separates high level policies from the mechanisms that implement them at the data plane, to avoid hard-coding the policies in the system itself.
To do so, it uses three main abstractions: *filter*, *metric*, and *controller*.

- A **filter** is a piece of programming logic that a system administrator can inject into the data plane to perform custom computations.
  In Crystal, this concept includes from arbitrary computations on object requests, such as compression or encryption, to resource management such as bandwidth differentiation.

- A **metric** has the role to automate the execution of filters based on the information accrued from the system. There
  are two types of information sources. A first type that corresponds to the real-time measurements got from the running workloads, like the number of GET operations
  per second of a tenant or the IO bandwidth allocated to a data container. As with filters, a fundamental feature of workload metrics is that they can be deployed at runtime.
  A second type of source is the metadata from the objects themselves. Such metadata is typically associated with read and write requests and includes properties like the size or type of data objects.

- The **controller** is the algorithm that manages the behavior of the data plane based on monitoring metrics.
  A controller may contain a very simple rule to enforce compression filter on a tenant, or it may execute a complex bandwidth differentiation algorithm requiring global visibility of the cluster.

.. figure:: http://crystal-sds.org/wp-content/uploads/2016/05/architecture9-768x575.png

   Crystal Architecture