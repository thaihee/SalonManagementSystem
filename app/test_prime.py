import pytest
from app.utils import is_prime
def test_true():
    assert is_prime(2) == True