import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="[MESSAGING UTILITY]: %(levelname)s %(asctime)s %(name)s:%(lineno)s %(message)s",  # noqa
)

# Rabbit Config
RABBIT_USER = os.getenv("RABBIT_USER", None)
RABBIT_PASSWORD = os.getenv("RABBIT_PASSWORD", None)
RABBIT_HOST_IP = os.getenv("RABBIT_HOST_IP", None)
RABBIT_PORT = int(os.getenv("RABBIT_PORT", 5672))
RABBIT_VHOST = os.getenv("RABBIT_VHOST", None)
RABBIT_CONNECTION_TIMEOUT = int(
    os.getenv("RABBIT_CONNECTION_TIMEOUT", 60 * 60 * 6)
)  # six hours

RABBIT_CONNECTION_CLOSED_RETRY = int(os.getenv("RABBIT_CONNECTION_CLOSED_RETRY", 3))
