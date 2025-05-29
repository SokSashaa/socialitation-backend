import random
import string


def generate_random_name(length=12)->str:
    chars = string.ascii_lowercase + string.digits  # буквы + цифры
    return ''.join(random.choices(chars, k=length))