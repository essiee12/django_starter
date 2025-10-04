import random
import string


def generate_otp(length=6, chars=string.digits):
    """
    Generate a random 6 digit OTP code of numbers.
    """
    first_digit = random.choice("123456789")
    remaining_digits = "".join(random.choice(chars) for _ in range(length - 1))
    return first_digit + remaining_digits
