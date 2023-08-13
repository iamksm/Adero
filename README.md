# Messaging Utility

This Python project demonstrates the usage of RabbitMQ for both Publish-Subscribe (PubSub) and Remote Procedure Call (RPC) communication patterns. RabbitMQ is a popular message broker that facilitates communication between different parts of a distributed application.

## Table of Contents
- [Introduction](#introduction)
- [Requirements](#requirements)
- [Getting Started](#getting-started)
- [Dependencies](#dependencies)
- [PubSub Usage](#pubsub-usage)
  - [Publisher](#publisher)
  - [Subscriber](#subscriber)
- [RPC Usage](#rpc-usage)
  - [Server](#server)
  - [Client](#client)
- [Adding Concurrency](#adding-concurrency)
- [Conclusion](#conclusion)

## Introduction
This project demonstrates how to utilize RabbitMQ for both Publish-Subscribe and Remote Procedure Call communication patterns in Python. The Publish-Subscribe pattern allows one-to-many distribution of messages, while the Remote Procedure Call pattern allows invoking methods on a remote server.

## Requirements
- Python 3.7+
- [pika](https://pypi.org/project/pika/): A Python library for RabbitMQ interactions

## Getting Started
1. Ensure you have RabbitMQ installed locally. You can follow the instructions [here](https://www.rabbitmq.com/download.html).

2. Install the required dependencies using `pip` to your virtualenv

    ```bash
    pip install pika
    ```

3. Copy and paste the provided code snippets into your Python files, adjusting configurations and queue/exchange names as needed.

4. Run the Publisher, Subscriber, Server, and Client scripts as needed for your use case.
messaging_utility
- Python 3.7+
- [pika](https://pypi.org/project/pika/)


## PubSub Usage
### Publisher
Publishes a message to a specified queue and exchange.

```python
from messaging_utility.pubsub.publisher import Publisher

# Configure RabbitMQ connection
config = {
    "RABBIT_USER": "guest",
    "RABBIT_PASSWORD": "guest",
    "RABBIT_HOST_IP": "localhost",
    "RABBIT_PORT": 5672,
    "RABBIT_VHOST": "",
    "RABBIT_CONNECTION_TIMEOUT": 60 * 60 * 6,
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
from messaging_utility.pubsub.subscriber import Subscriber

# Configure RabbitMQ connection
config = {
    "RABBIT_USER": "guest",
    "RABBIT_PASSWORD": "guest",
    "RABBIT_HOST_IP": "localhost",
    "RABBIT_PORT": 5672,
    "RABBIT_VHOST": "",
    "RABBIT_CONNECTION_TIMEOUT": 60 * 60 * 6,
}

# Processing function for received messages
def process_data(msg):
    # Your processing here
    print(msg)

    # Return True if message was processed successfully
    successfully_processed = True
    return successfully_processed

# Create a Subscriber instance
sub = Subscriber("TEST-QUEUE", "TEST-EXCHANGE", config, process_data)

# Start consuming messages
sub.consume()
```

## RPC Usage
### Server
Sets up a server to listen for RPC requests and processes them.

```python
from messaging_utility.rpc.server import RPCServer

# Fibonacci sequence generator function
def fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n - 1) + fib(n - 2)

# Configure RabbitMQ connection
config = {
    "RABBIT_USER": "guest",
    "RABBIT_PASSWORD": "guest",
    "RABBIT_HOST_IP": "localhost",
    "RABBIT_PORT": 5672,
    "RABBIT_VHOST": "",
    "RABBIT_CONNECTION_TIMEOUT": 60 * 60 * 6,
}

# Create an RPC Server instance
server = RPCServer("<YOUR_RPC_QUEUE>", "<YOUR_RPC_EXCHANGE>", config, fib)

# Start listening for requests
server.listen()
```

### Client
Sends RPC requests to the server and receives responses.

```python
from messaging_utility.rpc.client import RPCClient

# Configure RabbitMQ connection
config = {
    "RABBIT_USER": "guest",
    "RABBIT_PASSWORD": "guest",
    "RABBIT_HOST_IP": "localhost",
    "RABBIT_PORT": 5672,
    "RABBIT_VHOST": "",
    "RABBIT_CONNECTION_TIMEOUT": 60 * 60 * 6,
}

# Create an RPC Client instance
client_rpc = RPCClient("<YOUR_RPC_QUEUE>", "<YOUR_RPC_EXCHANGE>", config)

# Send requests and receive responses
for number in range(1, 31):
    response = client_rpc.call(number)
    print(f"Got {int(response)}")
```

## Adding Concurrency
You can add concurrency using ThreadPoolExecutor to process multiple RPC requests concurrently.

```py
import os
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from messaging_utility.rpc.client import RPCClient

# Configure RabbitMQ connection
config = {
    "RABBIT_USER": "guest",
    "RABBIT_PASSWORD": "guest",
    "RABBIT_HOST_IP": "localhost",
    "RABBIT_PORT": 5672,
    "RABBIT_VHOST": "",
    "RABBIT_CONNECTION_TIMEOUT": 60 * 60 * 6,
}

# Define the request processing function
def process_requests(i):
    client_rpc = RPCClient("<YOUR_RPC_QUEUE>", "<YOUR_RPC_EXCHANGE>", config)
    print(f" [x] Requesting fib({i})")
    response = client_rpc.call(i)
    print(f" [.] Got {int(response)}")

# Set number of workers
cpu_count = os.cpu_count()
number_of_workers = cpu_count() // 2 or cpu_count

# Create a ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=number_of_workers) as t_exe:
    threads = t_exe.map(process_requests, range(1, 31))
    deque(threads, maxlen=0)
```

## Conclusion
This Python project demonstrates the usage of RabbitMQ for both Publish-Subscribe and Remote Procedure Call communication patterns. By following the provided examples, you can integrate RabbitMQ into your applications to achieve efficient and scalable communication between components.
