#  Crystal: Open and Extensible Software-Defined Storage for OpenStack Swift

Crystal is a transparent, dynamic and open Software-Defined Storage (SDS) system for [OpenStack Swift](http://swift.openstack.org). 

### Documentation

The Crystal documentation is auto-generated after every commit and available online at http://crystal-controller.readthedocs.io/en/latest/

### Crystal Source code

Crystal source code is structured in several components:

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

To build the APIs in an easy way we use [Django REST Framework](http://www.django-rest-framework.org/).

## Requirements

* Python 2.7
* OpenStack Swift cluster with Keystone authentication.
* Redis server
* RabbitMQ server

## Installation

1. Clone the Crystal controller repository
2. Install Python package dependencies: `pip install -r requirements.txt`
3. Install PyActive:
    1. `git clone https://github.com/cloudspaces/pyactive.git`
    2. `cd pyactive/pyactive_project`
    3. `python setup.py develop`
4. Edit Crystal controller settings file `api/api/settings.py`: configure Swift proxy IP and port, Keystone IP, OpenStack credentials, Redis location, RabbitMQ credentials.
5. You can start the server running the following command from the source folder (`./api`): `python manage.py runserver 0.0.0.0:8000`.

## Usage

API usage is detailed in the [API specification](http://crystal-controller.readthedocs.io/en/latest/index.html#controller-api-specification).

A convenient [web dashboard](https://github.com/iostackproject/SDS-dashboard) is also available to simplify these API calls. Refer to the [dashboard overview](http://crystal-controller.readthedocs.io/en/latest/components/dashboard.html) for detailed information.

### Tests

Run unit tests from the source folder (`./api`) with the following command: `python manage.py test`

## Support

Please [open an issue](https://github.com/Crystal-SDS/controller/issues/new) for support.

## Contributing

Please contribute using [Github Flow](https://guides.github.com/introduction/flow/). Create a branch, add commits, and [open a pull request](https://github.com/Crystal-SDS/controller/compare/).

For more information, please visit [crystal-sds.org](http://crystal-sds.org/).

### Development VM

The easiest way to start using Crystal is to download the Development Virtual Machine.

The Development VM runs a Swift-all-in-one cluster together with Storlets and Crystal controller and middlewares.
It also includes an extended version of the OpenStack Dashboard that simplifies the management of Crystal filters, metrics and policies.

Download the Development VM from the following URL:

* ftp://ast2-deim.urv.cat/s2caio_vm
