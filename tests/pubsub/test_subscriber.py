import unittest
from unittest.mock import Mock, patch

from pika.exceptions import ChannelClosed, ConnectionClosed

from adero.pubsub.subscriber import Subscriber, SubscriberException


class TestSubscriber(unittest.TestCase):
    def setUp(self):
        self.queue_name = "TEST_QUEUE"
        self.exchange = "TEST_EXCHANGE"
        self.config = {
            "RABBIT_USER": "guest",
            "RABBIT_PASSWORD": "guest",
            "RABBIT_HOST_IP": "localhost",
            "RABBIT_PORT": 5672,
            "RABBIT_VHOST": "",
            "ENCRYPTION_KEY": b"b_xC4_-c3qo5TYmNhVO5MmtSbhutoLiHaxRomO1dszc=",
        }
        self.custom_data_processor = Mock()

    def test_init_raises_exception_if_missing_config(self):
        config = {}
        with self.assertRaises(SubscriberException):
            Subscriber(
                self.queue_name,
                self.exchange,
                config,
                self.custom_data_processor,
            )

    def test_init_raises_exception_custom_data_processor_is_not_a_callable(self):
        with self.assertRaises(SubscriberException):
            Subscriber(
                self.queue_name,
                self.exchange,
                self.config,
                None,
            )

    @patch("adero.pubsub.subscriber.pika")
    def test_create_connection_to_rabbitmq_host(self, mock_pika):
        subscriber = Subscriber(
            self.queue_name,
            self.exchange,
            self.config,
            self.custom_data_processor,
        )

        mock_pika.BlockingConnection.assert_called_once_with(
            mock_pika.URLParameters.return_value
        )
        mock_pika.URLParameters.assert_called_once_with(
            "amqp://guest:guest@localhost:5672/?blocked_connection_timeout=300"
        )
        subscriber.channel.exchange_declare.assert_called_once_with(
            exchange=self.exchange, exchange_type="direct", durable=True
        )
        assert subscriber.channel.queue_declare.call_count == 2
        assert subscriber.channel.queue_bind.call_count == 2

    def test_callback_calls_custom_data_processor(self):
        subscriber = Subscriber(
            self.queue_name,
            self.exchange,
            self.config,
            self.custom_data_processor,
        )
        msg = subscriber.serializer.encode_data({"test": "message"})
        msg = subscriber.security.encrypt_message(msg)

        mock_channel = Mock()
        mock_method = Mock()
        properties = Mock(app_id="1")

        subscriber.callback(mock_channel, mock_method, properties, msg)

        msg = {"data": {"test": "message"}, "properties": properties.__dict__}
        self.custom_data_processor.assert_called_once_with(msg)

    def test_callback_calls_basic_ack_if_processing_successful(self):
        subscriber = Subscriber(
            self.queue_name,
            self.exchange,
            self.config,
            self.custom_data_processor,
        )
        msg = subscriber.serializer.encode_data({"test": "message"})
        encrypted_data = subscriber.security.encrypt_message(msg)
        self.custom_data_processor.return_value = True
        mock_channel = Mock()
        mock_method = Mock()
        mock_props = Mock(app_id="1")

        subscriber.callback(mock_channel, mock_method, mock_props, encrypted_data)

        mock_channel.basic_ack.assert_called_once_with(
            delivery_tag=mock_method.delivery_tag
        )

    def test_callback_calls_basic_nack_if_processing_unsuccessful(self):
        subscriber = Subscriber(
            self.queue_name,
            self.exchange,
            self.config,
            self.custom_data_processor,
        )
        msg = subscriber.serializer.encode_data({"test": "message"})
        msg = subscriber.security.encrypt_message(msg)

        subscriber.custom_data_processor.return_value = False
        mock_channel = Mock()
        mock_method = Mock()
        mock_props = Mock(app_id="1")

        subscriber.callback(mock_channel, mock_method, mock_props, msg)

        mock_channel.basic_nack.assert_called_once_with(
            delivery_tag=mock_method.delivery_tag, requeue=False
        )

    def test_callback_calls_basic_reject_if_processing_unsuccessful_on_failed_queue(
        self,
    ):
        subscriber = Subscriber(
            f"FAILED-{self.queue_name}",
            self.exchange,
            self.config,
            self.custom_data_processor,
        )
        msg = subscriber.serializer.encode_data({"test": "message"})
        msg = subscriber.security.encrypt_message(msg)

        subscriber.custom_data_processor.return_value = False
        mock_channel = Mock()
        mock_method = Mock()
        mock_props = Mock(app_id="1")

        subscriber.callback(mock_channel, mock_method, mock_props, msg)

        mock_channel.basic_reject.assert_called_once_with(
            delivery_tag=mock_method.delivery_tag, requeue=True
        )

    @patch("adero.pubsub.subscriber.pika")
    def test_consume_calls_create_connection_to_rabbitmq_host_if_closed(
        self, mock_pika
    ):
        subscriber = Subscriber(
            self.queue_name,
            self.exchange,
            self.config,
            self.custom_data_processor,
        )

        assert mock_pika.BlockingConnection.call_count == 1
        subscriber.connection.is_closed = True
        subscriber.channel.is_closed = True

        subscriber.consume()

        assert mock_pika.BlockingConnection.call_count == 2
        new_connection = mock_pika.BlockingConnection.return_value
        assert subscriber.connection == new_connection
        assert subscriber.channel == new_connection.channel.return_value

    @patch("adero.pubsub.subscriber.pika")
    def test_consume_calls_start_consuming(self, mock_pika):
        subscriber = Subscriber(
            self.queue_name,
            self.exchange,
            self.config,
            self.custom_data_processor,
        )

        subscriber.connection.is_closed = False
        subscriber.channel.is_closed = False
        subscriber.consume()

        subscriber.channel.basic_consume.assert_called_once_with(
            queue=self.queue_name, on_message_callback=subscriber.callback
        )
        subscriber.channel.start_consuming.assert_called_once()

    @patch("adero.pubsub.subscriber.pika.BlockingConnection")
    def test_consume_connection_closed_exception(self, mock_blocking_connection):
        client = Subscriber(
            self.queue_name, self.exchange, self.config, self.custom_data_processor
        )
        client.retries = 1
        client.channel.is_closed = False
        client.connection.is_closed = False
        client.channel.start_consuming.side_effect = ConnectionClosed(
            404, "Connection closed"
        )

        client.consume()

        assert client.retries == 0

    @patch("adero.pubsub.subscriber.pika.BlockingConnection")
    def test_consume_channel_closed_exception(self, mock_blocking_connection):
        client = Subscriber(
            self.queue_name, self.exchange, self.config, self.custom_data_processor
        )
        client.retries = 1
        client.channel.is_closed = False
        client.connection.is_closed = False
        client.channel.start_consuming.side_effect = ChannelClosed(
            404, "Channel closed"
        )

        client.consume()

        assert client.retries == 0

    @patch("adero.pubsub.subscriber.pika.BlockingConnection")
    @patch("adero.pubsub.subscriber.SubscriberException")
    def test_consume_keyboard_interrupt(
        self, mock_subscriber_exception, mock_blocking_connection
    ):
        client = Subscriber(
            self.queue_name, self.exchange, self.config, self.custom_data_processor
        )
        client.channel.start_consuming.side_effect = KeyboardInterrupt

        client.create_connection_to_rabbitmq_host = Mock()
        client.channel.close = Mock()
        client.connection.close = Mock()

        client.consume()

        self.assertTrue(client.channel.stop_consuming.called)
        self.assertTrue(client.channel.close.called)
        self.assertTrue(client.connection.close.called)

    @patch("adero.pubsub.subscriber.pika")
    def test_subscriber_initialization_with_failed_queue(self, mock_pika):
        subscriber = Subscriber(
            f"FAILED-{self.queue_name}",
            self.exchange,
            self.config,
            self.custom_data_processor,
        )

        self.assertFalse(subscriber.requeue_msg_to_failed_queue)
        self.assertEqual(subscriber.requeue_queue, f"FAILED-{self.queue_name}")
