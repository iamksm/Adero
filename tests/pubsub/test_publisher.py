from unittest import TestCase

import pytest

from messaging_utility.pubsub.publisher import LOGGER, Publisher, PublisherException


class TestPublisher(TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.config = {
            "RABBIT_USER": "guest",
            "RABBIT_PASSWORD": "guest",
            "RABBIT_HOST_IP": "localhost",
            "RABBIT_PORT": 5672,
            "RABBIT_VHOST": "",
        }

    # Tests that Publisher class is successfully initialized with
    # provided queue name, exchange, and configuration dictionary.
    def test_publisher_initialization(self):
        queue_name = "test_queue"
        exchange = "test_exchange"
        publisher = Publisher(queue_name, exchange, self.config)
        assert publisher.rabbit_user == "guest"
        assert publisher.rabbit_password == "guest"
        assert publisher.rabbit_host_ip == "localhost"
        assert publisher.rabbit_port == 5672
        assert publisher.rabbit_vhost == ""
        assert publisher.connection_timeout == 21600
        assert publisher.queue_name == "TEST_QUEUE"
        assert publisher.exchange == "TEST_EXCHANGE"

    # Tests that data is successfully published to the specified queue.
    def test_publish_successfully(self):
        queue_name = "test_queue"
        exchange = "test_exchange"
        publisher = Publisher(queue_name, exchange, self.config)
        data = {"key": "value"}
        with self.assertLogs(LOGGER, level="INFO") as log:
            publisher.publish(data)
            log_msg = f" [x] Sent {data}"
            assert log_msg in log.output[0]

    def test_publish_with_connections_closed(self):
        queue_name = "test_queue"
        exchange = "test_exchange"
        publisher = Publisher(queue_name, exchange, self.config)

        # Close connetion
        publisher.connection.close()

        data = {"key": "value"}
        with self.assertLogs(LOGGER, level="INFO") as log:
            publisher.publish(data)
            log_msg = f" [x] Sent {data}"
            assert log_msg in log.output[0]

    # Tests PublisherException is raised if not all required configs are provided.
    def test_missing_config_raises_exception(self):
        config = {}
        queue_name = "test_queue"
        exchange = "test_exchange"
        with pytest.raises(PublisherException):
            Publisher(queue_name, exchange, config)

    # Tests exception is raised if not all required configs are provided.
    def test_required_configs_provided(self):
        queue_name = "test_queue"
        exchange = "test_exchange"
        with pytest.raises(PublisherException):
            Publisher(queue_name, exchange, {})

    # Tests that a connection to RabbitMQ is established successfully.
    def test_connection_established_successfully(self):
        queue_name = "test_queue"
        exchange = "test_exchange"
        publisher = Publisher(queue_name, exchange, self.config)
        assert publisher.connection.is_open

    # Tests that the channel to RabbitMQ is established successfully.
    def test_channel_established_successfully(self):
        publisher = Publisher("test_queue", "test_exchange", self.config)
        assert publisher.channel.is_open

    # Tests that the exchange is declared successfully.
    def test_exchange_declaration_success(self):
        queue_name = "test_queue"
        exchange = "test_exchange"
        publisher = Publisher(queue_name, exchange, self.config)
        assert publisher.channel.is_open
