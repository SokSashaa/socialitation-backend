from functools import wraps

from rest_framework.exceptions import NotAuthenticated

from socialize_main.utils.search_role import search_role


def check_role(permission_function):
    @wraps(permission_function)
    def wrapper(self, request, view):
        user = request.user

        if not user.is_authenticated:
            raise NotAuthenticated("Пользователь не аутентифицирован")


        if not hasattr(user,'role'):
            role_obj,role_name = search_role(user)

            user.role = role_name
            user.role_obj = role_obj

        return permission_function(self, request, view)

    return wrapper