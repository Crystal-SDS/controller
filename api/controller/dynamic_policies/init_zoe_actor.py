import re
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


def start_actors(controller_class):
    #host = create_host(crystal_settings.PYACTOR_URL)
    host = create_host('http://127.0.0.1:6375')  # creating a local host

    remote_host = host.lookup_url(crystal_settings.PYACTOR_URL, Host)  # looking up for Crystal controller existing host

    zoe_metric = remote_host.spawn("zoe_metric", 'controller.dynamic_policies.metrics.zoe_metric/ZoeMetric', ["zoe_metric", "amq.topic", "zoe_queue", "zoe"])

    try:
        zoe_metric.init_consum()
        sleep(0.1)
    except Exception as e:
        print e.args
        zoe_metric.stop_actor()

    klass = 'controller.dynamic_policies.rules.' + camel_to_snake(controller_class) + '/' + controller_class

    zoe_bw_controller = remote_host.spawn("zoe_bw_controller", 'controller.dynamic_policies.rules.zoe_bw_controller/ZoeBwController', ["zoe_bw_controller"])
    zoe_bw_controller.run("zoe_metric")


def camel_to_snake(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def main(argv):
    print "-- Settings configuration --"
    settings.configure(default_settings=crystal_settings)

    print "-- Starting Zoe actors --"
    set_context()
    start_actors(argv[0])

    sleep(1)
    shutdown()
    # serve_forever()

if __name__ == "__main__" and len(sys.argv) == 2:
    main(sys.argv[1:])
else:
    print 'usage: init_zoe_actor.py <zoe_controller>'
