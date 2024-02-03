import json
import logging
import uuid
from typing import Any, Dict

import pika

from adero.config.settings import settings

LOGGER = logging.getLogger(__name__)


class RPCClientException(Exception):
    pass


class RPCClient:
    def __init__(
        self,
        queue_name: str,
        exchange: str,
        config: Dict[str, Any],
    ) -> None:
        """
        Initializes the RPCClient class.

        Args:
            queue_name: The name of the queue to send requests to.
            exchange: The name of the exchange to send requests to.
            config: A dictionary containing the configuration parameters.
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
            raise RPCClientException("You need to provide all required configs")

        self.queue_name = queue_name.upper()
        self.exchange = exchange.upper()

        self.create_connection_to_rabbitmq_host()

    def create_connection_to_rabbitmq_host(self) -> None:
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

        self.init_consumer()

    def init_consumer(self) -> None:
        """
        Initializes the consumer by creating a callback queue
        and binding it to the exchange.
        """
        result = self.channel.queue_declare(queue="", exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.queue_bind(
            queue=self.callback_queue,
            exchange=self.exchange,
            routing_key=self.callback_queue,
        )

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True,
        )

        self.response = None
        self.corr_id = None

    def on_response(self, ch: Any, method: Any, props: Any, body: Any) -> None:
        """
        Callback function that sets the response attribute of the class
        when a response is received from the server.

        Args:
            ch: The channel object.
            method: The method object.
            props: The properties object.
            body: The body of the response.
        """
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, data: Dict[str, Any]):
        """
        Sends a request to the server using the RPC protocol and waits for a response.

        Args:
            data: The data to be sent as the request.

        Returns:
            The response received from the server.
        """
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange=self.exchange,
            routing_key=self.queue_name,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=json.dumps(data),
        )
        self.connection.process_data_events(time_limit=None)
        return self.response
