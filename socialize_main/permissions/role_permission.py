from rest_framework.permissions import BasePermission

from socialize_main.decorators.check_role import check_role
from socialize_main.utils.search_role import search_role


class RolePermission(BasePermission):
    def __init__(self, allowed_roles):
        self.allowed_roles = allowed_roles

    @check_role
    def has_permission(self, request, view):
        user = request.user

        # #Проверяем на аутентификацию пользователя
        # if not user.is_authenticated:
        #     return False

        # Проверяем доступно ли действие для указанной роли пользователя
        if hasattr(user, 'role'):
            role = user.role
        else:
            role_obj, role = search_role(user)

            request.user.role = role  # Сохраняем роль в объекте пользователя
            request.user.role_obj = role_obj  # Сохраняем объект роли в запросе

        if role in self.allowed_roles:
            return True

        return False
