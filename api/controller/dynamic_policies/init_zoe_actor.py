import sys
import os

THIS_FILE_PATH = os.path.dirname(os.path.abspath(__file__))

# Adding the root path to sys.path
sys.path.append(THIS_FILE_PATH.rsplit('/', 2)[0])

from pyactive.controller import init_host, serve_forever, start_controller
from eventlet import sleep

from django.conf import settings
from api import settings as crystal_settings


def start_actors():
    tcpconf = ('tcp', ('127.0.0.1', 6375))
    host = init_host(tcpconf)

    # metric = host.spawn_id("get_bw_info", 'metrics.bw_info', 'BwInfo', ["amq.topic", "get_bw_info", "bwdifferentiation.get_bw_info.#", "GET"])
    zoe_metric = host.spawn_id("zoe_metric", 'metrics.zoe_metric', 'ZoeMetric', ["zoe_metric", "amq.topic", "zoe_queue", "zoe"])

    try:
        zoe_metric.init_consum()
        sleep(0.1)
    except Exception as e:
        print e.args
        zoe_metric.stop_actor()

    zoe_bw_controller = host.spawn_id("zoe_bw_controller", 'rules.zoe_bw_controller', 'ZoeBwController', ["zoe_bw_controller"])
    zoe_bw_controller.run("zoe_metric")

    return host


def main():
    print "-- Settings configuration --"
    settings.configure(default_settings=crystal_settings)

    print "-- Starting Zoe actors --"
    start_controller('pyactive_thread')
    serve_forever(start_actors)


if __name__ == "__main__":
    main()
