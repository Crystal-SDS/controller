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

    message = json.dumps([{"tenant_id":tenant, "througput":bw}, {"tenant_id":tenant2, "througput":bw}])
    logging.info(' [*] Message sended is %s', message)
    channel.basic_publish(exchange='',
                          routing_key='througput',
                          body=message)

    sec +=  1
    time.sleep(1)
