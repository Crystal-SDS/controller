# Crystal Controller

[![Build Status](https://travis-ci.org/Crystal-SDS/controller.svg?branch=master)](https://travis-ci.org/Crystal-SDS/controller)
[![Coverage Status](https://coveralls.io/repos/github/Crystal-SDS/controller/badge.svg?branch=master)](https://coveralls.io/github/Crystal-SDS/controller?branch=master)
[![Code Health](https://landscape.io/github/Crystal-SDS/controller/master/landscape.svg?style=flat)](https://landscape.io/github/Crystal-SDS/controller/master)

This repository contains the code of Crystal Controller, the Software-Defined-Storage (SDS) REST API in the [IOStack](https://github.com/iostackproject) architecture.
It is a Django project that implements the REST API needed to handle filters, storlets and policies on top of Openstack Swift object-storage system. This API also includes a set of python processes who use
the [PyActor middleware](https://github.com/pedrotgn/pyactor), an Object Oriented implementation of the Actor model. This part allows to create simple policies using a DSL (integrated in the Crystal Controller API)
and to deploy them as an actor process, who analyze the system data thanks to the monitoring system, and allows to set or remove filters to tenants depending on the established policy.

To build the APIs in an easy way we use [Django REST Framework](http://www.django-rest-framework.org/).

## Requirements

* Python 2.7

* OpenStack Swift cluster with Keystone authentication.

* [RabbitMQ Server](https://www.rabbitmq.com/)

* [Redis Server](http://redis.io/)


## Installation

1. Clone the Crystal controller repository
```bash
git clone https://github.com/Crystal-SDS/controller /usr/share/crystal-controller
```
2. Install Python package dependencies: 
```bash
pip install -r /usr/share/crystal-controller/requirements.txt
```
3. Edit Crystal controller settings file `api/api/settings.py`: configure Swift proxy IP and port, Keystone IP, OpenStack credentials, Redis location, RabbitMQ credentials.
4. You can start the controller running the following command from the source folder (`/usr/share/crystal-controller/api`): 
```bash
python manage.py runserver 0.0.0.0:9000
```
5. Alternatively, it is possible to start the controller by using an Apache Http Server. Copy the config file to the Apache sites folder, and enable it.
```bash
cp /usr/share/crystal-controller/etc/apache2/sites-available/crystal_controller.conf /etc/apache2/sites-available/
a2ensite crystal_controller
service apache2 reload
```

## Usage

API usage is detailed in the [API specification](http://crystal-controller.readthedocs.io/en/latest/index.html#controller-api-specification).

A convenient [web dashboard](https://github.com/Crystal-SDS/dashboard) is also available to simplify these API calls. Refer to the [dashboard overview](http://crystal-controller.readthedocs.io/en/latest/components/dashboard.html) for detailed information.

### Tests

Run unit tests from the source folder (`./api`) with the following command: `python manage.py test`

## Support

Please [open an issue](https://github.com/Crystal-SDS/controller/issues/new) for support.

## Contributing

Please contribute using [Github Flow](https://guides.github.com/introduction/flow/). Create a branch, add commits, and [open a pull request](https://github.com/Crystal-SDS/controller/compare/).

For more information, please visit [crystal-sds.org](http://crystal-sds.org/).
