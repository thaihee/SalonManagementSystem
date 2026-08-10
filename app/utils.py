import math


def is_prime(n):
    if n < 2:
        raise ValueError('Invalid Number')
    for i in range(2, math.isqrt(n) + 1):
        if n % i == 0:
            return False
    return True