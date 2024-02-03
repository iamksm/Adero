import datetime
from decimal import Decimal

import msgpack


def extended_encoder(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()

    elif isinstance(obj, Decimal):
        return float(obj)

    return str(obj)


class RabbitSerializerException(Exception):
    ...


class RabbitSerializer:
    def encode_data(self, data):
        is_compatible_type = isinstance(data, (tuple, list, str, dict, int))
        if not is_compatible_type:
            msg_type = type(data)
            msg = f"{msg_type} is not in supported types (tuple, list, str, dict, int)"
            raise RabbitSerializerException(msg)

        msg = msgpack.packb(data, default=extended_encoder)
        return msg

    def decode_data(self, data):
        return msgpack.unpackb(data, raw=False)
