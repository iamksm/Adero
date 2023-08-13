import json
import logging
from time import time
from typing import Dict

import pika

from messaging_utility.config.settings import settings

LOGGER = logging.getLogger(__name__)


class PublisherException(Exception):
    ...


class Publisher:
    def __init__(self, queue_name: str, exchange: str, config: Dict[str, str]):
        """
        Initializes the Publisher class with the provided queue name,
        exchange, and configuration dictionary.

        Args:
            queue_name (str): The name of the queue to publish data to.
            exchange (str): The name of the exchange to bind the queue to.
            config (Dict[str, str]): The configuration dictionary
                containing RabbitMQ credentials and settings.
        """
        self.rabbit_user = config.get("RABBIT_USER", settings.RABBIT_USER)
        self.rabbit_password = config.get("RABBIT_PASSWORD", settings.RABBIT_PASSWORD)
        self.rabbit_host_ip = config.get("RABBIT_HOST_IP", settings.RABBIT_HOST_IP)
        self.rabbit_port = config.get("RABBIT_PORT", settings.RABBIT_PORT)
        self.rabbit_vhost = config.get("RABBIT_VHOST", settings.RABBIT_VHOST)
        self.connection_timeout = config.get(
            "RABBIT_CONNECTION_TIMEOUT", settings.RABBIT_CONNECTION_TIMEOUT
        )

        if not all(
            [
                self.rabbit_user,
                self.rabbit_password,
                self.rabbit_host_ip,
                self.rabbit_port,
                self.rabbit_vhost is not None,
                self.connection_timeout,
            ]
        ):
            raise PublisherException("You need to provide all required configs")

        self.queue_name = queue_name.upper()
        self.exchange = exchange.upper()

        self.create_connection_to_rabbitmq_host()

    def create_connection_to_rabbitmq_host(self):
        """
        Establishes a connection to the RabbitMQ host using the provided credentials.
        """
        timeout = f"blocked_connection_timeout={self.connection_timeout}"
        rabbit_url = f"amqp://{self.rabbit_user}:{self.rabbit_password}@{self.rabbit_host_ip}:{self.rabbit_port}/{self.rabbit_vhost}?{timeout}"  # noqa

        self.connection = pika.BlockingConnection(pika.URLParameters(rabbit_url))
        self.channel = self.connection.channel()

        self.channel.exchange_declare(
            exchange=self.exchange, exchange_type="direct", durable=True
        )

        self.channel.queue_declare(
            queue=self.queue_name,
            durable=True,
        )

        self.channel.queue_bind(
            queue=self.queue_name,
            exchange=self.exchange,
            routing_key=self.queue_name,
        )

    def publish(self, data, message_properties: Dict = dict()):
        """
        Publishes the provided data to the specified queue.

        Args:
            data (Dict, List,Tuple, String): The data to be published.

        Raises:
            pika.exceptions.ConnectionClosed: If the connection to RabbitMQ is closed.
            pika.exceptions.ChannelClosed: If the channel to RabbitMQ is closed.
        """
        if self.connection.is_closed or self.channel.is_closed:
            self.create_connection_to_rabbitmq_host()

        body = json.dumps(data)
        content_encoding = message_properties.get("content_encoding", "utf-8")

        expire_after = str(24 * 60 * 60 * 1000)  # (24 hrs)
        msg_props = {
            "delivery_mode": pika.spec.PERSISTENT_DELIVERY_MODE,
            "expiration": expire_after,  # Sets a TTL for the message in milliseconds.
            "timestamp": int(time()),  # timestamp when the message was sent.
            "content_encoding": content_encoding,
        }
        msg_props.update(message_properties) if message_properties else ...

        self.channel.basic_publish(
            exchange=self.exchange,
            routing_key=self.queue_name,
            body=body.encode(content_encoding),
            mandatory=True,
            properties=pika.BasicProperties(**msg_props),
        )
        LOGGER.info(f" [x] Sent {data}")
