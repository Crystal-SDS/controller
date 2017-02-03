#  Crystal: Open and Extensible Software-Defined Storage for OpenStack Swift

Crystal is a transparent, dynamic and open Software-Defined Storage (SDS) system for [OpenStack Swift](http://swift.openstack.org).

As depicted in the figure below, Crystal separates high level policies from the mechanisms that implement them at the data plane, to avoid hard-coding the policies in the system itself.
To do so, it uses three main abstractions: _filter_, _metric_, and _controller_.

A **filter** is a piece of programming logic that a system administrator can inject into the data plane to perform custom computations. 
In Crystal, this concept includes from arbitrary computations on object requests, such as compression or encryption, to resource management such as bandwidth differentiation.

A **metric** has the role to automate the execution of filters based on the information accrued from the system. There
are two types of information sources. A first type that corresponds to the real-time measurements got from the running workloads, like the number of GET operations
per second of a tenant or the IO bandwidth allocated to a data container. As with filters, a fundamental feature of workload metrics is that they can be deployed at runtime.
A second type of source is the metadata from the objects themselves. Such metadata is typically associated with read and write requests and includes properties like the size or type of data objects.

The **controller** is the algorithm that manages the behavior of the data plane based on monitoring metrics. 
A controller may contain a very simple rule to enforce compression filter on a tenant, or it may execute a complex bandwidth differentiation algorithm requiring global visibility of the cluster.

![alt text](http://crystal-sds.org/wp-content/uploads/2016/05/architecture2-1.png "Crystal Architecture")

### Crystal Source code

Crystal source code is structured in several sub-projects:

* **Controller**: this project. The Crystal control plane that offers dynamic meta-programming facilities over the data plane.

* **[Metric middleware](https://github.com/Crystal-SDS/metric-middleware)**: the middleware (data plane) that executes metrics that enable controllers to dynamically respond to workload changes in real time.

* **[Filter middleware](https://github.com/Crystal-SDS/filter-middleware)**: the middleware (data plane) that executes storage filters that intercept object flows to run computations or perform transformations on them.

* **[Dashboard](https://github.com/iostackproject/SDS-dashboard/tree/urv_dev)**: A user-friendly dashboard to manage policies, filters and workload metrics.

# Crystal Controller

[![Build Status](https://travis-ci.org/Crystal-SDS/controller.svg?branch=master)](https://travis-ci.org/Crystal-SDS/controller)
[![Coverage Status](https://coveralls.io/repos/github/Crystal-SDS/controller/badge.svg?branch=master)](https://coveralls.io/github/Crystal-SDS/controller?branch=master)
[![Code Health](https://landscape.io/github/Crystal-SDS/controller/master/landscape.svg?style=flat)](https://landscape.io/github/Crystal-SDS/controller/master)

This repository contains the code of Crystal Controller, the Software-Defined-Storage (SDS) REST API in the [IOStack](https://github.com/iostackproject) architecture.
It is a Django project that implements the REST API needed to handle filters, storlets and policies on top of Openstack Swift object-storage system. This API also includes a set of python processes who use
the [PyActive middleware](https://github.com/cloudspaces/pyactive), an Object Oriented implementation of the Actor model. This part allows to create simple policies using a DSL (integrated in the Crystal Controller API)
and to deploy them as an actor process, who analyze the system data thanks to the monitoring system, and allows to set or remove filters to tenants depending on the established policy.

The repository is structured with the next folders:

* **doc:** The doc folder includes the API specifications where you can find all the calls and parameters accepted by the SDS Controller.

* **puppet:** In this folder you can find two subfolders more. The manifests folder, that contains all the config files of the puppet (To read more about puppet click [here](http://docs.vagrantup.com/v2/provisioning/puppet_apply.html)). On the other hand, the modules folder that contains all dependencies added by puppet. Remember that these modules only are a link to the original repository, so when you clone this repository you need to add the modules or cloning in recursive way. (To read more about submodules click [here](https://git-scm.com/book/en/v2/Git-Tools-Submodules))

* **scripts:** The scripts folder contains all the scripts needed for the project. The file vagrant-init.sh will be executed each time that you start the virtual machine using vagrant.

* **api:** The folder contains the API source code. Its structure follows a standard Django project structure.

* **dynamic_policies** The dynamic_policies contains the source code of this part.

* **Vagrantfile:** This is the vagrant config file, where we define all the information that vagrant needs to start a virtual machine with all the requirements.

To build the APIs in an easy way we use [Django REST Framework](http://www.django-rest-framework.org/).

## Requirements

This project includes a Vagrant environment with all the dependencies (Django, pyactive, swiftclient, ...), so the only two requirements are:

1. Install [Virtualbox](https://www.virtualbox.org/)
2. Install [Vagrant](https://www.vagrantup.com/downloads.html)

## Installation

Once you have already installed the requirements, you only need to go to the project location using a terminal, and execute the command: `vagrant up`. First time, the process may take a few minutes because Vagrant downloads the Operative System to create the Virtual Machine. Next time the process will be faster.

The Virtual Machine that we started has all the tools that we need to run the server. To connect to this machine you only need to run the command `vagrant ssh`. The repository folder is synchronized between the local machine and the Virtual Machine, so you can develop the code in your local machine with your preferred IDE, and run the project in the Virtual Machine.

You can start the server using the command into the source folder (./api): `python manage.py runserver 0.0.0.0:8000`. After that, the server starts, and if you prefer to call Crystal controller from the host machine the port to use is `18000`. For instance, to list the Storlets from the host machine the URL should be: localhost:18000/storlets.

If some problem appears, make sure that:

1. redis-server service is running? Crystal Controller API stores the meta-data information in redis.
2. is PyActive in the PYTHONPATH? At home folder you can find the pyactive folder, where you can find another install.txt, please follow this steps.
3. review the settings file from Crystal Controller and make sure to write the correct IPs (Swift IP, Keystone IP, PyActive IP)

## Usage

API usage is detailed in the [API specification](/doc/api_specification.md).

A convenient [web dashboard](https://github.com/iostackproject/SDS-dashboard) is also available to simplify these API calls. Refer to the [dashboard overview](/doc/dashboard_overview.md) for detailed information.

### Tests

Run unit tests from the source folder (`./api`) with the following command: `python manage.py test`

## Support

Please [open an issue](https://github.com/Crystal-SDS/controller/issues/new) for support.

## Contributing

Please contribute using [Github Flow](https://guides.github.com/introduction/flow/). Create a branch, add commits, and [open a pull request](https://github.com/Crystal-SDS/controller/compare/).

For more information, please visit [crystal-sds.org](http://crystal-sds.org/).

### Development VM

There is an available development Virtual Machine which emulates running a Swift-all-in-one cluster together with Storlets and Crystal controller and middlewares. 
It also includes an extended version of the OpenStack Dashboard that simplifies the management of Crystal filters, metrics and policies.

* ftp://ast2-deim.urv.cat/s2caio_vm
