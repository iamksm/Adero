from adero.utilities.generate_key import generate_key


def test_generate_key():
    key = generate_key()
    assert isinstance(key, bytes)
