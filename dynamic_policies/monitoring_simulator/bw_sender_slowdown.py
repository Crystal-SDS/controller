import pika
import daemon
import logging
import math
import json
import time

# with daemon.DaemonContext():

logging.basicConfig(filename='/var/log/bw_consumer.log', format='%(asctime)s %(message)s', level=logging.INFO)

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

logging.info('[*] Start to publish messages')
sec = 0
tenant = "2312"
tenant2 = "2321"
while True:

    bw = (math.cos(sec)-1)*(-50)

    message = json.dumps([{"tenant_id":tenant, "slowdown":bw}, {"tenant_id":tenant2, "slowdown":bw}])
    logging.info(' [*] Message sended is %s', message)
    channel.basic_publish(exchange='',
                          routing_key='slowdown',
                          body=message)

    sec += 0.1
    time.sleep(1)
