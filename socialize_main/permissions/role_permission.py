from rest_framework.permissions import BasePermission

from socialize_main.utils.search_role import search_role


class RolePermission(BasePermission):
    def __init__(self, allowed_roles):
        self.allowed_roles = allowed_roles

    def has_permission(self, request, view):
        user = request.user

        #Проверяем на аутентификацию пользователя
        if not user.is_authenticated:
            return False

        # Проверяем доступно ли действие для указанной роли пользователя
        if hasattr(user, 'role'):
            role = user.role
            role_obj = user.role_obj
        else:
            role_obj, role = search_role(user)

        if role in self.allowed_roles:
            request.user.role = role  # Сохраняем роль в объекте пользователя
            request.user.role_obj = role_obj  # Сохраняем объект роли в запросе
            return True

        return False
