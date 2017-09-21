import sys
import os

# Adding the root path to sys.path
THIS_FILE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.append(THIS_FILE_PATH.rsplit('/', 2)[0])

#from pyactive.controller import init_host, serve_forever, start_controller
from pyactor.context import create_host, Host, serve_forever, set_context, sleep, shutdown
from eventlet import sleep

from django.conf import settings
from api import settings as crystal_settings

def stop_actors():
    host = create_host('http://127.0.0.1:6375')  # creating a local host

    print 'Before remote_host lookup'

    remote_host = host.lookup_url(crystal_settings.PYACTOR_URL, Host)  # looking up for Crystal controller existing host

    print 'After remote_host lookup'

    zoe_bw_controller = remote_host.lookup("zoe_bw_controller")

    print 'After zoe_bw_controller lookup'

    zoe_bw_controller.stop_actor()

    zoe_metric = remote_host.lookup("zoe_metric")
    zoe_metric.stop_actor()

def main():
    print "-- Settings configuration --"
    settings.configure(default_settings=crystal_settings)

    print "-- Stopping Zoe actors --"
    set_context()
    stop_actors()

    sleep(1)
    shutdown()


if __name__ == "__main__":
    main()
