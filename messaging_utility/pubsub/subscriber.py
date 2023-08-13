import json
import logging
from typing import Callable, Dict

import pika
from pika.exceptions import ChannelClosed, ConnectionClosed

from messaging_utility.config.settings import settings

LOGGER = logging.getLogger(__name__)


class SubscriberException(Exception):
    pass


class Subscriber:
    def __init__(
        self,
        queue_name: str,
        exchange: str,
        config: Dict,
        custom_data_processor: Callable,
    ):
        self.rabbit_user = config.get("RABBIT_USER", settings.RABBIT_USER)
        self.rabbit_password = config.get("RABBIT_PASSWORD", settings.RABBIT_PASSWORD)
        self.rabbit_host_ip = config.get("RABBIT_HOST_IP", settings.RABBIT_HOST_IP)
        self.rabbit_port = config.get("RABBIT_PORT", settings.RABBIT_PORT)
        self.rabbit_vhost = config.get("RABBIT_VHOST", settings.RABBIT_VHOST)
        self.connection_timeout = config.get(
            "RABBIT_CONNECTION_TIMEOUT", settings.RABBIT_CONNECTION_TIMEOUT
        )
        self.retries = settings.RABBIT_CONNECTION_CLOSED_RETRY

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
            raise SubscriberException("You need to provide all required configs")

        self.queue_name = queue_name.upper()
        self.exchange = exchange.upper()

        self._validate_custom_data_processor(custom_data_processor)

        self.create_connection_to_rabbitmq_host()

    def _validate_custom_data_processor(self, custom_data_processor: Callable):
        if not callable(custom_data_processor):
            error_msg = (
                f"{custom_data_processor} should be an un-executed method or function"
            )
            raise SubscriberException(error_msg)
        self.custom_data_processor = custom_data_processor

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

    def callback(self, ch, method, properties, body):
        """
        The function processes received messages from the RabbitMQ queue.
        """
        msg = json.loads(body)

        is_successfully_processed = self.custom_data_processor(msg)
        if is_successfully_processed:
            LOGGER.info(f" [x] DONE PROCESSING {msg}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            LOGGER.warning(f" [x] COULD NOT PROCESS {msg}, THIS WILL BE REQUEUED")
            ch.basic_nack(delivery_tag=method.delivery_tag)

    def consume(self):
        """
        Listens for messages in the specified RabbitMQ queue and processes them
        using the callback function. It continuously listens for new messages
        until interrupted by the user or an exception occurs.
        """
        try:
            if self.connection.is_closed or self.channel.is_closed:
                self.create_connection_to_rabbitmq_host()

            self.channel.basic_consume(
                queue=self.queue_name, on_message_callback=self.callback
            )

            LOGGER.info(" [*] Waiting for messages. To exit press CTRL+C")

            self.channel.start_consuming()
        except (ConnectionClosed, ChannelClosed):
            LOGGER.warning("CONNECTION CLOSED BY THE BROKER!!!")

            if self.retries > 0:
                LOGGER.info("RE-INITIALIZING QUEUED MESSAGES CONSUMPTION")
                self.retries -= 1
                self.consume()

            LOGGER.error("SHUTTING DOWN RPC SERVER AFTER RESTART ATTEMPTS!!!")
        except KeyboardInterrupt:
            self.channel.stop_consuming()
            self.channel.close()
            self.connection.close()
