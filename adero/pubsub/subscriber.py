import logging
import time
from pprint import pformat
from typing import Callable, Dict

import pika
from pika.exceptions import AMQPError

from adero.utilities import RabbitSecurity, RabbitSerializer

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
        self.rabbit_user = config.get("RABBIT_USER")
        self.rabbit_password = config.get("RABBIT_PASSWORD")
        self.rabbit_host_ip = config.get("RABBIT_HOST_IP")
        self.rabbit_port = int(config.get("RABBIT_PORT", 5672))
        self.rabbit_vhost = config.get("RABBIT_VHOST")
        self.connection_timeout = int(config.get("RABBIT_CONNECTION_TIMEOUT", 60 * 5))
        self.retries = int(config.get("RABBIT_CONNECTION_CLOSED_RETRY", 3))
        self.security_key = config.get("ENCRYPTION_KEY")

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
        self.security = RabbitSecurity(self.security_key)
        self.serializer = RabbitSerializer()

        # Only create a failed queue if we the current self.queue_name isn't one
        self.requeue_msg_to_failed_queue = True
        if "FAILED-" not in self.queue_name:
            self.requeue_queue = f"FAILED-{self.queue_name}"
        else:
            self.requeue_msg_to_failed_queue = False
            self.requeue_queue = self.queue_name

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

        if self.requeue_msg_to_failed_queue:
            # No need re-declare the failed queue we are working on
            self.channel.queue_declare(
                queue=self.requeue_queue,
                durable=True,
            )

            self.channel.queue_bind(
                queue=self.requeue_queue,
                exchange=self.exchange,
                routing_key=self.requeue_queue,
            )

    def callback(self, channel, method, properties, body):
        """
        The function processes received messages from the RabbitMQ queue.
        """
        decrypted_message = self.security.decipher_message(body)
        data = self.serializer.decode_data(decrypted_message)

        props = properties.__dict__ if properties else {}
        msg = {"data": data, "properties": props}

        if self.custom_data_processor(msg):
            LOGGER.debug(" ********************* DONE PROCESSING ******************** ")
            LOGGER.debug(pformat(data))
            LOGGER.debug(" ========================================================== ")
            channel.basic_ack(delivery_tag=method.delivery_tag)
        else:
            if self.requeue_msg_to_failed_queue:
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                channel.basic_publish(
                    exchange=self.exchange,
                    routing_key=self.requeue_queue,
                    body=body,
                    mandatory=True,
                    properties=properties,
                )
            else:
                # We are already working with the failed queue,
                # just return the message to the failed queue
                channel.basic_reject(delivery_tag=method.delivery_tag, requeue=True)

            LOGGER.error(f" ** PROCESSING FAILED, REQUEUED TO {self.requeue_queue} ** ")
            LOGGER.error(pformat(data))
            LOGGER.error(" ========================================================== ")

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
        except AMQPError:
            LOGGER.warning("CONNECTION CLOSED BY THE BROKER!!!")

            if self.retries > 0:
                LOGGER.debug("WAITING FOR 5 SECONDS TO REBOOT CONSUMER")
                time.sleep(5)
                LOGGER.info("RE-INITIALIZING QUEUED MESSAGES CONSUMPTION")
                self.retries -= 1
                self.consume()

            LOGGER.critical("SHUTTING DOWN CONSUMER AFTER ALL RESTART ATTEMPTS!!!")
        except KeyboardInterrupt:
            self.channel.stop_consuming()
            self.channel.close()
            self.connection.close()
