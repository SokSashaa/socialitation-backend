from rest_framework import permissions

from socialize_main.constants.roles import Roles
from socialize_main.models import Observed
from socialize_main.utils.search_role import search_role


class ChangeUserInfoPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user

        req_user_id = view.kwargs.get('pk')

        if not user.is_authenticated:
            return False

        if hasattr(user,'role'):
            role_user = user.role
        else:
            _, role_user = search_role(user)

        isNotAllow = role_user == Roles.TUTOR.value and not Observed.objects.filter(tutor=user,
                                                                                    user__id=req_user_id).exists()

        if isNotAllow:
            return False

        return True
