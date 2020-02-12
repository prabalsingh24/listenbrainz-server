#!/usr/bin/env python3

import json
import sys
import os
import pika
import ujson
import logging

from listenbrainz.listen import Listen
from time import time, sleep
import listenbrainz.utils as utils
from listenbrainz.listen_writer import ListenWriter

from listenbrainz.webserver import create_app
from flask import current_app
from requests.exceptions import ConnectionError

UPDATE_INTERVAL = 3


class RMQSnooperSubscriber(ListenWriter):

    def __init__(self):
        super().__init__()

        self.ls = None
        self.connection = None
        self.channel = None
        self.stats = {}
        self.t0 = 0.0
        self.last_update = 0.0


    def callback(self, ch, method, properties, body):
        listens = ujson.loads(body)
        self.process_listens(listens)

        while True:
            try:
                self.incoming_ch.basic_ack(delivery_tag = method.delivery_tag)
                break
            except pika.exceptions.ConnectionClosed:
                self.connect_to_rabbitmq()

        return True


    def process_listens(self, listens):
        """
            Examine listens and add counts to the stats that we're keeping
        """

        for listen in listens:
            user_name = listen['user_name']
            if not user_name in self.stats:
                self.stats[username] = 0

            self.stats[user_name] += 1

        if self.last_update > UPDATE_INTERVAL:
            self.print_stats()
            self.last_update = time()

   
    def print_stats(self):
        for k in sorted(self.stats, key=self.stats.get, reverse=True):
            print("%32s: %d" % (k, self.stats[k]))

        print()


    def start(self, app, exchange, queue):

        self.t0 = time()
        self.last_update = 0.0

        with app.app_context():
            self._verify_hosts_in_config()

            while True:
                self.connect_to_rabbitmq()
                self.channel = self.connection.channel()
                self.channel.exchange_declare(exchange=exchange, exchange_type='fanout')
                self.channel.queue_declare(queue, durable=True)
                self.channel.queue_bind(exchange, queue)
                self.channel.basic_consume(
                    lambda ch, method, properties, body: self.static_callback(ch, method, properties, body, obj=self),
                    queue=queue,
                )

                current_app.logger.info("rmq snooper started")
                try:
                    self.channel.start_consuming()
                except pika.exceptions.ConnectionClosed:
                    current_app.logger.warn("Connection to rabbitmq closed. Re-opening.", exc_info=True)
                    self.connection = None
                    continue

                self.connection.close()


if __name__ == "__main__":
    rmq = RMQSnooperSubscriber()
    app = create_app()
    rmq.start(app, app.config['INCOMING_EXCHANGE'], app.config['INCOMING_QUEUE'])
