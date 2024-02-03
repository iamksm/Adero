import ast
import datetime
import unittest
from uuid import UUID

from pytz import UTC

from adero.utilities.message_serializer import (
    Decimal,
    RabbitSerializer,
    RabbitSerializerException,
    msgpack,
)

test_data = {
    "status": "ACTIVE",
    "registered_on": datetime.datetime(2024, 2, 3, 6, 52, 8, tzinfo=UTC),
    "member_context": {
        "member_id": "12345678-90-ABCDE",
        "member_names": "JANE DOE",
        "membership_type": "PREMIUM",
        "extra": None,
        "debug": {
            "category_name": None,
            "policy_number": None,
            "book_number": "98765432",
        },
    },
    "visit_number": "87654321",
    "member_details": None,
    "authorization_token": None,
    "library_code": "456",
    "is_student": False,
    "location_name": "dev",
    "owner": "5678",
    "payer": "3003",
    "borrowed_books": (
        {
            "book_id": "22208520",
            "primary_document": None,
            "borrow_type": "LONG_TERM",
            "borrow_from": datetime.datetime(2024, 2, 3, 6, 52, 8, tzinfo=UTC),
            "return_due": datetime.datetime(2024, 2, 3, 10, 0, 0, tzinfo=UTC),
            "workflow_state": "BORROWED",
            "owner": "5678",
            "lines": (
                {
                    "book_line_no": "46022022",
                    "name": "THE GREAT GATSBY",
                    "quantity": 1.0,
                    "unit_price": Decimal("1000.00"),
                    "borrow_date": datetime.datetime(2024, 2, 3, 10, 0, 0, tzinfo=UTC),
                    "charge_master_code": None,
                    "charge_master_category": None,
                    "discount_amount": None,
                    "owner": "5678",
                },
                {
                    "book_line_no": "21749683",
                    "name": "TO KILL A MOCKINGBIRD",
                    "quantity": 1.0,
                    "unit_price": Decimal("2000.00"),
                    "borrow_date": datetime.datetime(2024, 2, 3, 10, 0, 0, tzinfo=UTC),
                    "charge_master_code": None,
                    "charge_master_category": None,
                    "discount_amount": None,
                    "owner": "5678",
                },
            ),
            "fines": (
                {
                    "fine_type": "LATE_RETURN",
                    "charge": Decimal("500.00"),
                    "charge_date": datetime.datetime(2024, 2, 3, 6, 52, 8, tzinfo=UTC),
                    "fine_number": "2220851920",
                    "owner": "5678",
                },
            ),
            "book_attachments": (),
        },
    ),
}


class TestRabbitSerializer(unittest.TestCase):
    def test_encoding_with_list(self):
        serializer = RabbitSerializer()
        data = [1, 2, 3]
        encoded_data = serializer.encode_data(data)
        decoded_data = serializer.decode_data(encoded_data)
        self.assertEqual(decoded_data, data)

    def test_encoding_with_string(self):
        serializer = RabbitSerializer()
        data = "hello"
        encoded_data = serializer.encode_data(data)
        decoded_data = serializer.decode_data(encoded_data)
        self.assertEqual(decoded_data, data)

    def test_encoding_with_dictionary(self):
        serializer = RabbitSerializer()
        data = {"key": "value"}
        encoded_data = serializer.encode_data(data)
        decoded_data = serializer.decode_data(encoded_data)
        self.assertEqual(decoded_data, data)

    def test_encoding_with_integer(self):
        serializer = RabbitSerializer()
        data = 123
        encoded_data = serializer.encode_data(data)
        decoded_data = serializer.decode_data(encoded_data)
        self.assertEqual(decoded_data, data)

    def test_decoding_with_valid_data(self):
        serializer = RabbitSerializer()
        data = b"\x93\x01\x02\x03"
        decoded_data = serializer.decode_data(data)
        self.assertEqual(decoded_data, [1, 2, 3])

    def test_encoding_with_unsupported_type(self):
        serializer = RabbitSerializer()
        data = {1, 2, 3}
        with self.assertRaises(RabbitSerializerException):
            serializer.encode_data(data)

    def test_decoding_with_invalid_data(self):
        serializer = RabbitSerializer()
        invalid_data = b"\x80\x01\x01"
        with self.assertRaises(msgpack.exceptions.ExtraData):
            serializer.decode_data(invalid_data)

    def test_encoding_with_datetime_fixed_fixed(self):
        serializer = RabbitSerializer()
        data = {"date": datetime.datetime.now()}
        encoded_data = serializer.encode_data(data)
        decoded_data = serializer.decode_data(encoded_data)
        self.assertEqual(decoded_data["date"], data["date"].isoformat())

    def test_encoding_with_date_object_fixed(self):
        serializer = RabbitSerializer()
        data = {"date": "2022-01-01"}
        encoded_data = serializer.encode_data(data)
        decoded_data = serializer.decode_data(encoded_data)
        self.assertEqual(decoded_data, data)

    def test_encoding_with_uuid_fixed(self):
        serializer = RabbitSerializer()
        data = {"uuid": UUID("123e4567-e89b-12d3-a456-426655440000")}
        encoded_data = serializer.encode_data(data)
        decoded_data = serializer.decode_data(encoded_data)
        self.assertEqual(decoded_data, {"uuid": str(data["uuid"])})

    def test_encoding_with_decimal(self):
        serializer = RabbitSerializer()
        data = {"value": Decimal("10.5")}
        encoded_data = serializer.encode_data(data)
        decoded_data = serializer.decode_data(encoded_data)
        self.assertEqual(decoded_data, data)

    def test_decoding_with_large_data(self):
        serializer = RabbitSerializer()
        data = list(range(1000000))
        encoded_data = serializer.encode_data(data)
        decoded_data = serializer.decode_data(encoded_data)
        self.assertEqual(decoded_data, data)

    def test_encoding_data_with_mixed_data_types(self):
        serializer = RabbitSerializer()
        msg = serializer.encode_data(test_data)
        assert isinstance(msg, bytes)

    def test_uncommon_object_encoding(self):
        serializer = RabbitSerializer()
        data = {"Name": "Kossam Ouma", "version": 3 + 5j}
        msg = serializer.encode_data(data)
        self.assertIsInstance(msg, bytes)  # Successful encoding

        decoded_msg = serializer.decode_data(msg)
        version = ast.literal_eval(decoded_msg["version"])
        self.assertEqual(version, data["version"])
