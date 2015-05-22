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
      pip        => true,
      dev        => true,
      virtualenv => true,
      gunicorn   => true,
    }
}
class { 'prepare':
    stage => first;
}

include prepare

$sysPackages = ['git', 'curl', 'graphviz', 'tree', 'nodejs']
package { $sysPackages:
  ensure => "installed",
  require  => Class['prepare']
}


class { 'postgresql::server':
    ip_mask_allow_all_users    => '0.0.0.0/0',
    listen_addresses           => '*',
    postgres_password          => 'postgres',
}

postgresql::server::db { 'sds_controller':
  user     => 'sds_controller_user',
  password => postgresql_password('sds_controller_user', 'sds_controller_pass');
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
}
