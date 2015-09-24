import pika
import daemon

with daemon.DaemonContext():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='hello2')

    print ' [*] Waiting for messages. To exit press CTRL+C'
    f2 = open('/home/vagrant/src/v.txt', 'w')
    f2.write('[*] Waiting for messages. To exit press CTRL+C')
    f2.close()
    f = open('/home/vagrant/src/a.txt', 'wa')
    def callback(ch, method, properties, body):
        f.write(" [x] Received "+str(body)+"\n")
    channel.basic_consume(callback,
                          queue='hello2',
                          no_ack=True)

    channel.start_consuming()
