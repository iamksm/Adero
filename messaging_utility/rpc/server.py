import json
import logging
from typing import Callable, Dict

import pika
from pika.exceptions import ChannelClosed, ConnectionClosed

from messaging_utility.config.settings import settings

LOGGER = logging.getLogger(__name__)


class RPCServerException(Exception):
    pass


class RPCServer:
    """
    A class for creating a connection to a RabbitMQ host and listening for RPC requests.

    Args:
        queue_name (str): The name of the queue to listen for RPC requests.
        exchange (str): The name of the exchange to use for RPC requests.
        config (Dict): A dictionary containing the RabbitMQ configuration parameters.
        custom_data_processor (Callable): A function that processes
            the incoming RPC requests.

    Raises:
        RPCServerException: If the custom_data_processor is not a callable function.

    Attributes:
        rabbit_user (str): The RabbitMQ username.
        rabbit_password (str): The RabbitMQ password.
        rabbit_host_ip (str): The RabbitMQ host IP address.
        rabbit_port (int): The RabbitMQ port number.
        rabbit_vhost (str): The RabbitMQ virtual host.
        connection_timeout (int): The RabbitMQ connection timeout.
        queue_name (str): The name of the queue to listen for RPC requests.
        exchange (str): The name of the exchange to use for RPC requests.
        custom_data_processor (Callable): A function that processes
            the incoming RPC requests.
        connection (pika.BlockingConnection): The RabbitMQ connection object.
        channel (pika.channel.Channel): The RabbitMQ channel object.
    """

    def __init__(
        self,
        queue_name: str,
        exchange: str,
        config: Dict,
        custom_data_processor: Callable,
    ):
        """
        Initializes the RPCServer class and creates a connection to the host.

        Args:
            queue_name (str): The name of the queue to listen for RPC requests.
            exchange (str): The name of the exchange to use for RPC requests.
            config (Dict): A dictionary containing the RabbitMQ config parameters.
            custom_data_processor (Callable): A function that processes
                the incoming RPC requests.

        Raises:
            RPCServerException: If the custom_data_processor is not a callable.
        """
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
            raise RPCServerException("You need to provide all required configs")

        self.queue_name = queue_name.upper()
        self.exchange = exchange.upper()

        self._validate_custom_data_processor(custom_data_processor)

        self.create_connection_to_rabbitmq_host()

    def _validate_custom_data_processor(self, custom_data_processor: Callable):
        """
        Validates the custom data processor function.

        Args:
            custom_data_processor (Callable): A function that processes
                the incoming RPC requests.

        Raises:
            RPCServerException: If the custom_data_processor is not a callable.
        """
        if not callable(custom_data_processor):
            error_msg = (
                f"{custom_data_processor} should be an un-executed method or function"
            )
            raise RPCServerException(error_msg)
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

    def on_request(self, ch, method, props, body):
        """
        Handles incoming RPC requests and responds to them using
        the custom data processor function.

        Args:
            ch (pika.channel.Channel): The RabbitMQ channel object.
            method (pika.spec.Basic.Deliver): The RabbitMQ method object.
            props (pika.spec.BasicProperties): The RabbitMQ properties object.
            body (bytes): The message body.

        Returns:
            None
        """
        msg = json.loads(body)

        function_name = self.custom_data_processor.__name__
        LOGGER.info(f" [.] {function_name}({msg})")

        response = self.custom_data_processor(int(msg))
        LOGGER.info(f" [x] RESPONDING TO {msg}")

        ch.basic_publish(
            exchange=self.exchange,
            routing_key=props.reply_to,
            properties=pika.BasicProperties(correlation_id=props.correlation_id),
            body=json.dumps(response),
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def listen(self):
        """
        Starts listening for RPC requests.

        Returns:
            None
        """
        try:
            if self.connection.is_closed or self.channel.is_closed:
                self.create_connection_to_rabbitmq_host()

            # self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=self.queue_name, on_message_callback=self.on_request
            )

            LOGGER.info(" [x] Awaiting RPC requests")
            self.channel.start_consuming()
        except (ChannelClosed, ConnectionClosed):
            LOGGER.warning("CONNECTION CLOSED BY THE BROKER!!!")

            if self.retries > 0:
                LOGGER.info("RE-INITIALIZING QUEUED MESSAGES CONSUMPTION")
                self.retries -= 1
                self.listen()

            LOGGER.error("SHUTTING DOWN RPC SERVER AFTER RESTART ATTEMPTS!!!")
        except KeyboardInterrupt:
            self.channel.stop_consuming()
            self.channel.close()
            self.connection.close()
