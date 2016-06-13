[![Stories in Ready](https://badge.waffle.io/iostackproject/SDS-Controller-for-Object-Storage.png?label=ready&title=Ready)](https://waffle.io/iostackproject/SDS-Controller-for-Object-Storage)
[![Stories in In Progress](https://badge.waffle.io/iostackproject/SDS-Controller-for-Object-Storage.png?label=In%20Progress&title=In%20Progress)](https://waffle.io/iostackproject/SDS-Controller-for-Object-Storage)


# Crystal-Controller

This repository contains the code of the SDS Controller for Object Storage in the IOStack architecture. The SDS Controller repository contains two differentiated parts: **The SDS Controller API** and the **Dynamic Policies**. The **SDS Controller API** is a Django project that implements the REST API needed to handle the Storlets and the BW Differentiation. Otherwise, **Dynamic Policies** is a set of python processes who use the [PyActive middleware](https://github.com/cloudspaces/pyactive) (an Object Oriented implementation of the Actor model). This part allows to create simple policies using a DSL (integrated in the SDS Controller API) and deploys them as an actor process, whose analyze the system data, thanks to the monitoring system, allows to set or remove filters to tenants depending of the policy established.

The repository is structured with the next folders:

* **doc:** The doc folder includes the API specifications. In this document you can find all the calls accepted by the SDS Controller. Furthermore, this document specifies all the parameters that each call needs.

* **puppet:** In this folder you can find two subfolders more. The manifests folder, that contains all the config files of the puppet (To read more about puppet click [here](http://docs.vagrantup.com/v2/provisioning/puppet_apply.html)). On the other hand, the modules folder that contains all dependencies added by puppet. Remember that these modules only are a link to the original repository, so when you clone this repository you need to add the modules or cloning in recursive way. (To read more about submodules click [here](https://git-scm.com/book/en/v2/Git-Tools-Submodules))

* **scripts:** The scripts folder contains all the scripts needed for the project. The file vagrant-init.sh will be executed each time that you start the virtual machine using vagrant.

* **sds_controller:** The sds_controller contains the source code. It's structure follows a standard Django project structure.

* **dynamic_policies** The dynamic_policies contains the source code of this part.

* **Vagrantfile:** This is the vagrant config file, where we define all the information that vagrant need to start a virtual machine with all the requirements.  

To build the APIs in an easy way we use [Django REST Framework](http://www.django-rest-framework.org/).

# Requirements

These project only have two requirements:

1. Install Virtual Box [Visit VirtualBox page!](https://www.virtualbox.org/)
2. Install Vagrant [Visit Vagrant page!](https://www.vagrantup.com/downloads.html)

That's all! You don't need Django or Python... Vagrant resolves this problem for us.

# Installation

Once you have already installed the requirements, you only need to go in the folder location using a terminal, and execute the command: `vagrant up`. First time, the process may take a few minutes because Vagrant downloads the Operative System to create the Virtual Machine. The other times the process will be faster.

The Virtual Machine that we started has all the tools that we need to run the server. To connect to this machine you only need to run the command `vagrant ssh`. The repository folder is synchronized between your machine and the Virtual Machine, so you can develop the code in your local machine with your prefer IDE, and run the project in the Virtual Machine.

You can start the server using the command into the source folder (src/sds_controller): ´python manage.py runserver 0.0.0.0:8000´. After that the server starts, and if you prefer to call the SDS controller for your machine the port to use is `18000`. For instance, to call to list the Storlets from your machine the url will be: localhost:18000/storlets. *We have in the TODO list to configure vagrant and puppet to do a deploy of the SDS Controller in Apache each time that starts the Virtual Machine.*

If some problem appear, make sure..

1. redis-server service is running? Start this service, because the SDS Controller API stores the meta-data information in redis.
2. is PyActive in the PYTHONPATH? At home folder you can found the pyactive folder, where you can find another install.txt, please follow this steps.
3. review the settings file from SDS Controller and make sure to write the correct IPs (Swift IP, Keystone IP, PyActive IP)


# Monitoring
<!-- out of date -->
To enable the monitoring module you need to follow this steps. First create a new queue at OpenStack controller host. You need to be logged into the OpenStack controller host and run this command: `sudo rabbitmqadmin declare queue name="myQueue" durable=true auto_delete=false` and assign a binding to it with the service you want to monitor with `sudo rabbitmqadmin declare binding source="ceilometer" destination_type="queue" destination="myQueue" routing_key="metering.sample"` where myQueue will be the name of the queue to retrieve the events.

`TODO:` Then, you need to edit the config file `x` and add the ip:port tuple of the RabbitMQ at OpenStack controller host (by default `rabbitmq_host_ip:5672`) and the name of the queue that you created before, myQueue in this lines.

# Future Work

- [x] Communicate Storlet module with OpenStack Swift.
- [x] Communicate BW module with OpenStack Swift.
- [x] Add Monitoring module and communicate with OpenStack Swift using RabbitMQ.
