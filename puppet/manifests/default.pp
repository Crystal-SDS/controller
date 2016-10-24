stage { 'first':
    before => Stage['main'];
}

class prepare {
    class { 'apt':
      update => {
        frequency => 'always',
      },
    }
    class { 'python' :
      version    => 'system',
      pip        => present,
      dev        => present,
      virtualenv => present,
      gunicorn   => present,
    }
}
class { 'prepare':
    stage => first;
}

include prepare

class rabbitmq_server {
  package { "rabbitmq-server":
    ensure => "installed",
    require  => Class['prepare'],
    provider => "aptitude"
  }

  service { "rabbitmq-server":
    ensure => running,
    require => Package["rabbitmq-server"],
  }
}

include rabbitmq_server

$sysPackages = ['git', 'curl', 'redis-server']
package { $sysPackages:
  ensure => "installed",
  require  => Class['prepare']
}

/*
	class { 'postgresql::server':
		ip_mask_allow_all_users    => '0.0.0.0/0',
		listen_addresses           => '*',
		postgres_password          => 'postgres',
	}

	postgresql::server::db { 'sds_controller':
	  user     => 'sds_controller_user',
	  password => postgresql_password('sds_controller_user', 'sds_controller_pass');
	}
*/
package { 'python-psycopg2':
    ensure => installed,
  }

package {
    "django":
        ensure => "1.8.1",
        provider => pip;
    "django-bootstrap3":
        ensure => "installed",
        provider => pip;
    "djangorestframework":
        ensure => "installed",
        provider => pip;
    "python-daemon":
        ensure => "installed",
        provider => pip;
    "pika":
        ensure => "0.9.8",
        provider => pip;
    "python-swiftclient":
        ensure => "installed",
        provider => pip;
    "python-keystoneclient":
        ensure => "installed",
        provider => pip;
    "redis":
        ensure => "installed",
        provider => pip;
    "Sphinx":
        ensure => "installed",
        provider => pip;
    "pyparsing":
        ensure => "installed",
        provider => pip;
}
