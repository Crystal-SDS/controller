=========
Dashboard
=========

Crystal provides a user-friendly dashboard to manage policies, filters and workload metrics.
The dashboard is completely integrated in the OpenStack Horizon project.
Moreover, Crystal integrates advanced monitoring analysis tools for administrators in order to explore the behavior tenants,
containers and even objects in the system and devise appropriate policies.

.. figure:: http://crystal-sds.org/wp-content/uploads/2016/05/nodes-1024x491.png
.. figure:: http://crystal-sds.org/wp-content/uploads/2016/05/storlet_filters-1024x407.png

   SDS Administration

.. figure:: http://crystal-sds.org/wp-content/uploads/2016/05/monitoring-1024x427.png

   Storage Monitoring

Demo videos
-----------

The following videos demonstrate some uses of Crystal SDS-Dashboard:

- `Crystal - My first storage policy`_: This tutorial will teach you how to write a storage policy with Crystal and install a storage filter.
  We show the how this enables dynamic reconfiguration of OpenStack Swift, which can be exploited to optimize storage workloads.
- `Crystal - Playing with Dynamic Storage Automation Policies`_: In this video we show how to use dynamic storage automation policies that are triggered by workload monitoring metrics.
- `Crystal - Multi-tenant Bandwidth Differentiation`_: In this video we show how Crystal can provide bandwidth differentiation in a multi-tenant OpenStack Swift deployment.

.. _Crystal - My first storage policy: https://www.youtube.com/watch?v=vbNxCbQbKWM
.. _Crystal - Playing with Dynamic Storage Automation Policies: https://www.youtube.com/watch?v=7DPhB9zN9zo
.. _Crystal - Multi-tenant Bandwidth Differentiation: https://www.youtube.com/watch?v=6JixYX3yXwY

Source code
-----------

Dashboard source code is available in the following repository branch: `SDS-Dashboard source code`_

.. _SDS-Dashboard source code: https://github.com/iostackproject/SDS-dashboard/tree/urv_dev