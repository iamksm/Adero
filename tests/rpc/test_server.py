import json
import unittest
from unittest.mock import Mock, patch

from messaging_utility.rpc.server import (
    ChannelClosed,
    RPCServer,
    RPCServerException,
)


class TestRPCServer(unittest.TestCase):
    def setUp(self):
        self.config = {
            "RABBIT_USER": "guest",
            "RABBIT_PASSWORD": "guest",
            "RABBIT_HOST_IP": "localhost",
            "RABBIT_PORT": 5672,
            "RABBIT_VHOST": "",
            "RABBIT_CONNECTION_TIMEOUT": 5,
        }
        self.queue_name = "test_queue"
        self.exchange = "test_exchange"
        self.custom_data_processor = Mock()

    @patch("messaging_utility.rpc.server.pika")
    def test_create_connection_to_rabbitmq_host(self, mock_pika):
        server = RPCServer(
            self.queue_name, self.exchange, self.config, self.custom_data_processor
        )

        mock_pika.BlockingConnection.assert_called_once_with(
            mock_pika.URLParameters.return_value
        )

        assert server.connection == mock_pika.BlockingConnection.return_value

    def test_on_request(self):
        server = RPCServer(
            self.queue_name, self.exchange, self.config, self.custom_data_processor
        )
        ch = Mock()
        method = Mock()
        props = Mock(reply_to="reply_queue", correlation_id="corr_id")
        body = json.dumps(5).encode()

        self.custom_data_processor.return_value = "response"
        self.custom_data_processor.__name__ = "custom_data_processor"
        server.on_request(ch, method, props, body)

        self.assertTrue(self.custom_data_processor.called)
        self.assertEqual(ch.basic_publish.call_count, 1)
        # Add assertions for the published response

    @patch("messaging_utility.rpc.server.pika.BlockingConnection")
    def test_init_invalid_custom_data_processor(self, mock_blocking_connection):
        with self.assertRaises(RPCServerException):
            RPCServer(
                self.queue_name, self.exchange, self.config, "invalid_processor"
            )

    @patch("messaging_utility.rpc.server.pika.BlockingConnection")
    def test_init_missing_configs(self, mock_blocking_connection):
        incomplete_config = {
            "RABBIT_USER": "user",
            "RABBIT_PASSWORD": "password",
            "RABBIT_HOST_IP": "localhost",
            "RABBIT_PORT": 5672,
        }
        with self.assertRaises(RPCServerException):
            RPCServer(
                self.queue_name,
                self.exchange,
                incomplete_config,
                self.custom_data_processor,
            )

    @patch("messaging_utility.rpc.server.pika.BlockingConnection")
    @patch("messaging_utility.rpc.server.pika.channel.Channel")
    def test_listen(self, mock_channel, mock_blocking_connection):
        server = RPCServer(
            self.queue_name, self.exchange, self.config, self.custom_data_processor
        )
        server.connection.is_closed = False
        server.channel.is_closed = False

        server.listen()

        self.assertTrue(server.channel.start_consuming.called)

    @patch("messaging_utility.rpc.server.pika.BlockingConnection")
    @patch("messaging_utility.rpc.server.pika.channel.Channel")
    def test_listen_keyboardinterrupt(self, mock_channel, mock_blocking_connection):
        server = RPCServer(
            self.queue_name, self.exchange, self.config, self.custom_data_processor
        )
        server.channel.is_closed = False
        server.channel.start_consuming.side_effect = KeyboardInterrupt

        server.listen()

        self.assertTrue(server.channel.stop_consuming.called)
        self.assertTrue(server.channel.close.called)
        self.assertTrue(server.connection.close.called)

    @patch("messaging_utility.rpc.server.pika.BlockingConnection")
    def test_consume_channel_closed_exception(self, mock_blocking_connection):
        server = RPCServer(
            self.queue_name, self.exchange, self.config, self.custom_data_processor
        )
        server.retry = 1
        server.channel.is_closed = False
        server.connection.is_closed = False
        server.channel.start_consuming.side_effect = ChannelClosed(
            404, "Channel closed"
        )

        server.listen()

        self.assertTrue(server.channel.basic_consume.called)
