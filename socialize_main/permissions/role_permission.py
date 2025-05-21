from rest_framework.permissions import BasePermission

from socialize_main.decorators.check_role import check_role
from socialize_main.utils.get_role import get_role


class RolePermission(BasePermission):
    def __init__(self, allowed_roles):
        self.allowed_roles = allowed_roles

    @check_role
    def has_permission(self, request, view):
        user = request.user

        role = get_role(user)

        return role in self.allowed_roles