# Crystal

[Crystal](http://crystal-sds.org/) is a transparent, dynamic and open Software-Defined Storage (SDS) system for [OpenStack Swift](http://swift.openstack.org).
It is structured in several sub-projects:

* [Controller](https://github.com/Crystal-SDS/controller): the Crystal control plane that offers dynamic meta-programming facilities over the data plane.

* [Introspection middleware](https://github.com/Crystal-SDS/introspection-middleware): the inspection triggers (data plane), that enable controllers to dynamically respond to workload changes in real time.

* [Filter middleware](https://github.com/Crystal-SDS/filter-middleware): the storage filters (data plane), that intercept object flows and run computations or perform transformations on them.

* [Dashboard](https://github.com/iostackproject/SDS-dashboard/tree/urv_dev): A user-friendly dashboard to manage policies, filters and workload metrics.

![alt text](http://crystal-sds.org/wp-content/uploads/2016/05/architecture9-768x575.png "Crystal Architecture")

# Crystal Controller

[![Build Status](https://travis-ci.org/Crystal-SDS/controller.svg?branch=master)](https://travis-ci.org/Crystal-SDS/controller)
[![Coverage Status](https://coveralls.io/repos/github/Crystal-SDS/controller/badge.svg?branch=master)](https://coveralls.io/github/Crystal-SDS/controller?branch=master)
[![Code Health](https://landscape.io/github/Crystal-SDS/controller/master/landscape.svg?style=flat)](https://landscape.io/github/Crystal-SDS/controller/master)

This repository contains the code of Crystal Controller, the Software-Defined-Storage (SDS) REST API in the [IOStack](https://github.com/iostackproject) architecture.
It is a Django project that implements the REST API needed to handle filters, storlets and policies on top of Openstack Swift object-storage system. This API also includes a set of python processes who use
the [PyActive middleware](https://github.com/cloudspaces/pyactive), an Object Oriented implementation of the Actor model. This part allows to create simple policies using a DSL (integrated in the Crystal Controller API)
and to deploy them as an actor process, who analyze the system data thanks to the monitoring system, and allows to set or remove filters to tenants depending on the established policy.

The repository is structured with the next folders:

* **doc:** The doc folder includes the API specifications. In this document you can find all the calls accepted by the SDS Controller. Furthermore, this document specifies all the parameters that each call needs.

* **puppet:** In this folder you can find two subfolders more. The manifests folder, that contains all the config files of the puppet (To read more about puppet click [here](http://docs.vagrantup.com/v2/provisioning/puppet_apply.html)). On the other hand, the modules folder that contains all dependencies added by puppet. Remember that these modules only are a link to the original repository, so when you clone this repository you need to add the modules or cloning in recursive way. (To read more about submodules click [here](https://git-scm.com/book/en/v2/Git-Tools-Submodules))

* **scripts:** The scripts folder contains all the scripts needed for the project. The file vagrant-init.sh will be executed each time that you start the virtual machine using vagrant.

* **api:** The folder contains the API source code. Its structure follows a standard Django project structure.

* **dynamic_policies** The dynamic_policies contains the source code of this part.

* **Vagrantfile:** This is the vagrant config file, where we define all the information that vagrant needs to start a virtual machine with all the requirements.

To build the APIs in an easy way we use [Django REST Framework](http://www.django-rest-framework.org/).

## Requirements

This project includes a Vagrant environment with all the dependencies (Django, pyactive, swiftclient, ...), so the only two requirements are:

1. Install Virtual Box [Visit VirtualBox page!](https://www.virtualbox.org/)
2. Install Vagrant [Visit Vagrant page!](https://www.vagrantup.com/downloads.html)

## Installation

Once you have already installed the requirements, you only need to go to the project location using a terminal, and execute the command: `vagrant up`. First time, the process may take a few minutes because Vagrant downloads the Operative System to create the Virtual Machine. Next time the process will be faster.

The Virtual Machine that we started has all the tools that we need to run the server. To connect to this machine you only need to run the command `vagrant ssh`. The repository folder is synchronized between the local machine and the Virtual Machine, so you can develop the code in your local machine with your preferred IDE, and run the project in the Virtual Machine.

You can start the server using the command into the source folder (./api): `python manage.py runserver 0.0.0.0:8000`. After that, the server starts, and if you prefer to call Crystal controller from the host machine the port to use is `18000`. For instance, to list the Storlets from the host machine the URL should be: localhost:18000/storlets.

If some problem appears, make sure that:

1. redis-server service is running? SDS Controller API stores the meta-data information in redis.
2. is PyActive in the PYTHONPATH? At home folder you can find the pyactive folder, where you can find another install.txt, please follow this steps.
3. review the settings file from SDS Controller and make sure to write the correct IPs (Swift IP, Keystone IP, PyActive IP)

## Usage

API usage is detailed in the [API specification](/doc/api_specification.md).

A convenient [web dashboard](https://github.com/iostackproject/SDS-dashboard) is also available to simplify these API calls. Refer to the [dashboard overview](/doc/dashboard_overview.md) for detailed information.

### Tests

Run unit tests from the source folder (`./api`) with the following command: `python manage.py test`

## Support

Please [open an issue](https://github.com/Crystal-SDS/controller/issues/new) for support.

## Contributing

Please contribute using [Github Flow](https://guides.github.com/introduction/flow/). Create a branch, add commits, and [open a pull request](https://github.com/Crystal-SDS/controller/compare/).
