import sys
import os

# Adding the root path to sys.path
THIS_FILE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.append(THIS_FILE_PATH.rsplit('/', 2)[0])

#from pyactive.controller import init_host, serve_forever, start_controller
from pyactor.context import create_host, serve_forever, set_context
from eventlet import sleep

from django.conf import settings
from api import settings as crystal_settings

def start_actors():
    host = create_host(crystal_settings.PYACTOR_URL)

    zoe_metric = host.spawn("zoe_metric", 'controller.dynamic_policies.metrics.zoe_metric/ZoeMetric', ["zoe_metric", "amq.topic", "zoe_queue", "zoe"])

    try:
        zoe_metric.init_consum()
        sleep(0.1)
    except Exception as e:
        print e.args
        zoe_metric.stop_actor()

    zoe_bw_controller = host.spawn("zoe_bw_controller", 'controller.dynamic_policies.rules.zoe_bw_controller/ZoeBwController', ["zoe_bw_controller"])
    zoe_bw_controller.run("zoe_metric")

    return host


def main():
    print "-- Settings configuration --"
    settings.configure(default_settings=crystal_settings)

    print "-- Starting Zoe actors --"
    set_context()
    start_actors()
    serve_forever()


if __name__ == "__main__":
    main()
