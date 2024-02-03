# Adero

This Python project demonstrates the usage of RabbitMQ for both Publish-Subscribe (PubSub) and Remote Procedure Call (Request Response Usage) communication patterns. RabbitMQ is a popular message broker that facilitates communication between different parts of a distributed application.

## Table of Contents

- [Introduction](#introduction)
- [Requirements](#requirements)
- [Getting Started](#getting-started)
- [Dependencies](#dependencies)
- [PubSub Usage](#pubsub-usage)
  - [Publisher](#publisher)
  - [Subscriber](#subscriber)
- [Request Response Usage](#request_response-usage)
  - [Server](#server)
  - [Client](#client)
- [Adding Concurrency](#adding-concurrency)
- [Conclusion](#conclusion)

## Introduction

This project demonstrates how to utilize RabbitMQ for both Publish-Subscribe and Remote Procedure Call communication patterns in Python. The Publish-Subscribe pattern allows one-to-many distribution of messages, while the Remote Procedure Call pattern allows invoking methods on a remote server.

## Requirements

- [Python 3.7+](https://www.python.org/downloads/)
- [RabbitMQ](https://www.rabbitmq.com/download.html)

## Getting Started

1. Ensure you have RabbitMQ installed locally. You can follow the instructions [here](https://www.rabbitmq.com/download.html).

2. Install the required dependencies using `pip` to your virtualenv

    ```bash
    pip install -e .
    ```

3. Copy and paste the provided code snippets into separate terminals, adjusting configurations and queue/exchange names as needed.

    a. Create 2 new terminals and run [Publisher](#publisher) and [Subscriber](#subscriber) (PubSub).

    b. Create 2 new terminals and run [Server](#server) and [Client](#client) (Request Response Usage).

## Dependencies

- [pika](https://pika.readthedocs.io/en/stable/)
- [cryptography](https://cryptography.io/en/latest/)
- [msgpack](https://msgpack.org/index.html)

## PubSub Usage

### Publisher

Publishes a message to a specified queue and exchange.

```python
from adero.pubsub.publisher import Publisher

# Configure RabbitMQ connection
config = {
    "RABBIT_USER": "guest",
    "RABBIT_PASSWORD": "guest",
    "RABBIT_HOST_IP": "localhost",
    "RABBIT_PORT": 5672,
    "RABBIT_VHOST": "",
    "RABBIT_CONNECTION_TIMEOUT": 60 * 5,
    # has to be the same with what you will use in the subscriber
    "ENCRYPTION_KEY": b'b_xC4_-c3qo5TYmNhVO5MmtSbhutoLiHaxRomO1dszc='
}

# Create a Publisher instance
pub = Publisher("TEST-QUEUE", "TEST-EXCHANGE", config)

# Message to publish
msg = {
    "FirstName": "Kossam",
    "LastName": "Ouma",
    "Age": 18,
    "Children": ["First born", "Last born"]
}

# Publish the message
pub.publish(msg)
```

### Subscriber

Receives and processes messages from the specified queue.

```python
from adero.pubsub.subscriber import Subscriber

# Configure RabbitMQ connection
config = {
    "RABBIT_USER": "guest",
    "RABBIT_PASSWORD": "guest",
    "RABBIT_HOST_IP": "localhost",
    "RABBIT_PORT": 5672,
    "RABBIT_VHOST": "",
    "RABBIT_CONNECTION_TIMEOUT": 60 * 5,
    # has to be the same with what you used in the publisher
    "ENCRYPTION_KEY": b'b_xC4_-c3qo5TYmNhVO5MmtSbhutoLiHaxRomO1dszc='
}

# Processing function for received messages
def process_data(msg):
    # Your processing here
    my_data = msg["data"]
    message_properties = msg["properties"]  # is an instance of pika.BasicProperties

    print(f"My data - {my_data}, message properties - {message_properties}")

    # Return True if message was processed successfully
    successfully_processed = True
    return successfully_processed

# Create a Subscriber instance
sub = Subscriber("TEST-QUEUE", "TEST-EXCHANGE", config, process_data)

# Start consuming messages
sub.consume()
```

## Request Response Usage

### Server

Sets up a server to listen for Request Response Usage requests and processes them.

```python
from adero.request_response.server import Server

# Fibonacci sequence generator function
def multiply_by_2(msg):
    number = msg.get("data")
    return number * 2

# Configure RabbitMQ connection
config = {
    "RABBIT_USER": "guest",
    "RABBIT_PASSWORD": "guest",
    "RABBIT_HOST_IP": "localhost",
    "RABBIT_PORT": 5672,
    "RABBIT_VHOST": "",
    "RABBIT_CONNECTION_TIMEOUT": 60 * 5,
    # has to be the same with what you used in the client
    "ENCRYPTION_KEY": b'b_xC4_-c3qo5TYmNhVO5MmtSbhutoLiHaxRomO1dszc='
}

# Create an Request Response Usage Server instance
server = Server("<YOUR_RPC_QUEUE>", "<YOUR_RPC_EXCHANGE>", config, multiply_by_2)

# Start listening for requests
server.listen()
```

### Client

Sends Request Response Usage requests to the server and receives responses.

```python
from adero.request_response.client import Client

# Configure RabbitMQ connection
config = {
    "RABBIT_USER": "guest",
    "RABBIT_PASSWORD": "guest",
    "RABBIT_HOST_IP": "localhost",
    "RABBIT_PORT": 5672,
    "RABBIT_VHOST": "",
    "RABBIT_CONNECTION_TIMEOUT": 60 * 5,
    # has to be the same with what you used in the server
    "ENCRYPTION_KEY": b'b_xC4_-c3qo5TYmNhVO5MmtSbhutoLiHaxRomO1dszc='
}

# Create an Request Response Usage Client instance
client_rpc = Client("<YOUR_RPC_QUEUE>", "<YOUR_RPC_EXCHANGE>", config)

# Send requests and receive responses
for number in range(1, 31):
    response = client_rpc.call(number)

    my_data = response["data"]
    message_properties = response["properties"]  # is an instance of pika.BasicProperties

    print(f"Response - {my_data}")
    print(f"message properties - {message_properties}\n")
```

## Adding Concurrency

You can add concurrency using ThreadPoolExecutor to process multiple Request Response Usage requests concurrently.

```py
import os
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from adero.request_response.client import Client

# Configure RabbitMQ connection
config = {
    "RABBIT_USER": "guest",
    "RABBIT_PASSWORD": "guest",
    "RABBIT_HOST_IP": "localhost",
    "RABBIT_PORT": 5672,
    "RABBIT_VHOST": "",
    "RABBIT_CONNECTION_TIMEOUT": 60 * 5,
    # has to be the sametime with what you used in the publisher
    "ENCRYPTION_KEY": b'b_xC4_-c3qo5TYmNhVO5MmtSbhutoLiHaxRomO1dszc='
}

# Define the request processing function
def process_requests(i):
    client_rpc = Client("<YOUR_RPC_QUEUE>", "<YOUR_RPC_EXCHANGE>", config)
    print(f" [x] Requesting fib({i})")
    response = client_rpc.call(i)

    my_data = response["data"]
    message_properties = response["properties"]  # is an instance of pika.BasicProperties

    print(f"My data - {my_data}, message properties - {message_properties}")

# Set number of workers
cpu_count = os.cpu_count()
number_of_workers = cpu_count() // 2 or cpu_count

# Create a ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=number_of_workers) as t_exe:
    t_exe.map(process_requests, range(1, 31))
```

## Note

To generate a valid **ENCRYPTION_KEY** you need to run the below
and have that as an environment variable across the apps you will be using adero on.

```py
from adero import generate_key

key = generate_key()
print(key)
```

## Conclusion

This Python project demonstrates the usage of RabbitMQ for both Publish-Subscribe and Remote Procedure Call communication patterns. By following the provided examples, you can integrate RabbitMQ into your applications to achieve efficient and scalable communication between components.
