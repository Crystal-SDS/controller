#!/usr/bin/python

"""
Simple script to send a message to the zoe queue
"""

import pika
import sys


def main(argv):
    credentials = pika.PlainCredentials('guest', 'guest')
    parameters = pika.ConnectionParameters(host='localhost', port=5672, credentials=credentials)

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    message = argv[0] + ':' + argv[1]
    channel.basic_publish(exchange='amq.topic', routing_key='zoe', body=message)

if __name__ == "__main__" and len(sys.argv) == 3:
    main(sys.argv[1:])
else:
    print 'usage: send_zoe_message.py <tenant> <abstract_policy>'
