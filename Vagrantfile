# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
  config.vm.box = "ubuntu/trusty32"
  config.vm.hostname = "sds-controller-vm"

  config.vm.network "forwarded_port", guest: 5432, host: 15432 # Postgresql
  config.vm.network "forwarded_port", guest: 8000, host: 18000 # Django
  config.vm.network "forwarded_port", guest: 5672, host: 25672 #rabitmq
  config.vm.network "forwarded_port", guest: 15672, host: 35672 #rabitmq

  config.vm.synced_folder ".", "/home/vagrant/src"

  config.vm.provider "virtualbox" do |vb|
    vb.gui = false
    vb.memory = "1024"
  end

  config.vm.provision :puppet do |puppet|
    puppet.manifests_path = "puppet/manifests"
    puppet.module_path = "puppet/modules"
  end

  config.vm.provision "shell", path: "scripts/vagrant-init.sh"

end
