import re


def get_integrity_error_user(error):
    error_message = str(error)
    print(error_message)
    if re.search(r'unique.*email.*exists', error_message, re.I | re.S):
        return 'Указанная почта уже занята'
    elif re.search(r'unique.*phone_number.*exists', error_message, re.I | re.S):
        return 'Указанный телефон уже занят'
    elif 'user_and_tutor_cannot_be_the_same' in error_message:
        return 'Наблюдаемый и тьютор не могут быть одним пользователем'
    elif 'unique' in error_message:
        return 'Ошибка уникальности данных'

    return 'Ошибка целостности данных'
