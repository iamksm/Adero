import unittest
from unittest.mock import Mock, patch

from messaging_utility.rpc.client import RPCClient, RPCClientException


class TestRPCClient(unittest.TestCase):
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

    @patch("messaging_utility.rpc.client.pika")
    def test_create_connection_to_rabbitmq_host(self, mock_pika):
        client = RPCClient(self.queue_name, self.exchange, self.config)

        mock_pika.BlockingConnection.assert_called_once_with(
            mock_pika.URLParameters.return_value
        )

        assert client.connection == mock_pika.BlockingConnection.return_value

    @patch("messaging_utility.rpc.client.pika.BlockingConnection")
    def test_init_consumer(self, mock_blocking_connection):
        client = RPCClient(self.queue_name, self.exchange, self.config)
        client.create_connection_to_rabbitmq_host()
        client.init_consumer()

        # Add assertions for callback queue creation and binding

    def test_on_response(self):
        client = RPCClient(self.queue_name, self.exchange, self.config)
        client.corr_id = "test_corr_id"
        method = Mock()
        props = Mock(correlation_id="test_corr_id")
        body = "response_data"

        client.on_response(Mock(), method, props, body)
        self.assertEqual(client.response, body)

    def test_on_response_corr_id_mismatch(self):
        client = RPCClient(self.queue_name, self.exchange, self.config)
        client.corr_id = "test_corr_id"
        method = Mock()
        props = Mock(correlation_id="wrong_corr_id")
        body = "response_data"

        client.on_response(Mock(), method, props, body)
        self.assertIsNone(client.response)

    @patch("messaging_utility.rpc.client.pika.BlockingConnection")
    def test_call(self, mock_blocking_connection):
        client = RPCClient(self.queue_name, self.exchange, self.config)
        client.create_connection_to_rabbitmq_host()

        test_data = {"key": "value"}
        test_response = "test_response"
        mock_blocking_connection.return_value.process_data_events.side_effect = (
            lambda time_limit: setattr(client, "response", test_response)
        )

        response = client.call(test_data)

        self.assertEqual(client.response, test_response)
        self.assertEqual(response, test_response)
        # Add more assertions related to message publishing and correlation ID

    def test_missing_config(self):
        incomplete_config = {
            "RABBIT_USER": "user",
            "RABBIT_PASSWORD": "password",
            "RABBIT_HOST_IP": "localhost",
            "RABBIT_PORT": 5672,
        }
        with self.assertRaises(RPCClientException):
            RPCClient(self.queue_name, self.exchange, incomplete_config)
