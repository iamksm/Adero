import logging
from time import sleep, time
from typing import Dict

import pika
from pika.exceptions import AMQPError

from adero.utilities import RabbitSecurity, RabbitSerializer

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
        self.rabbit_user = config.get("RABBIT_USER")
        self.rabbit_password = config.get("RABBIT_PASSWORD")
        self.rabbit_host_ip = config.get("RABBIT_HOST_IP")
        self.rabbit_port = int(config.get("RABBIT_PORT", 5672))
        self.rabbit_vhost = config.get("RABBIT_VHOST")
        self.connection_timeout = int(config.get("RABBIT_CONNECTION_TIMEOUT", 60 * 5))
        self.security_key = config.get("ENCRYPTION_KEY")
        self.retry_count = 1

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
        self.security = RabbitSecurity(self.security_key)
        self.serializer = RabbitSerializer()

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
        Publishes the provided data to the specified queue in RabbitMQ.

        This method establishes a connection to the RabbitMQ host,
        serializes the data to JSON format, sets message properties
        such as delivery mode and expiration time, and publishes the data to the queue.

        Args:
            data (Dict, List, Tuple, String): The data to be published.
            message_properties Dict: Additional message properties (default: {}).

        Raises:
            ConnectionError: If the connection to RabbitMQ cannot be established.
        """
        try:
            if not isinstance(message_properties, dict):
                error = PublisherException(
                    "`message_properties` needs to be of type dict"
                )
                LOGGER.error(error)
                return

            if self.connection.is_closed or self.channel.is_closed:
                self.create_connection_to_rabbitmq_host()

            msg = self.serializer.encode_data(data)
            encrypted_message = self.security.encrypt_message(msg)

            expire_after = str(24 * 60 * 60 * 1000)  # (24 hrs)
            msg_props = {
                "delivery_mode": pika.spec.PERSISTENT_DELIVERY_MODE,
                # Sets a TTL for the message in milliseconds.
                "expiration": expire_after,
                # timestamp when the message was sent.
                "timestamp": int(time()),
            }
            msg_props.update(message_properties) if message_properties else ...

            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=self.queue_name,
                body=encrypted_message,
                mandatory=True,
                properties=pika.BasicProperties(**msg_props),
            )
            LOGGER.info(f" [x] Sent {data}")
        except AMQPError as e:
            if self.retry_count <= 5:
                # For every failure, retry after (60 * x) seconds
                # Where x is the retry count.
                # eg First retry, we will wait and retry after 1 min
                # Third retry we will wait and retry after 3 min
                wait_time = 60  # seconds
                wait_time *= self.retry_count
                sleep(wait_time)
                self.retry_count += 1
                return self.publish(data, message_properties)

            exception = PublisherException(
                f"Unable to publish to {self.queue_name} due to: \n{e}"
            )
            LOGGER.critical(exception)
            raise exception from e
        except Exception as e:
            LOGGER.critical(PublisherException(e))
