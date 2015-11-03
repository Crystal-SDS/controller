import pika
import daemon
import logging

with daemon.DaemonContext():

    logging.basicConfig(filename='/var/log/bw_consumer.log', format='%(asctime)s %(message)s', level=logging.INFO)

    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='test_consumer')

    logging.info(' [*] Waiting for messages')

    def callback(ch, method, properties, body):
        logging.info(" [x] Received "+str(body)+"\n")
        #Here we can call SDS Controller API.
    channel.basic_consume(callback,
                          queue='test_consumer',
                          no_ack=True)

    channel.start_consuming()
