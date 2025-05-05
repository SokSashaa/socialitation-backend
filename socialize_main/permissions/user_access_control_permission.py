from rest_framework import permissions

from socialize_main.constants.roles import Roles
from socialize_main.decorators.check_role import check_role
from socialize_main.models import Observed
from socialize_main.utils.get_param_from_request import get_param_from_request
from socialize_main.utils.get_role import get_role
from socialize_main.utils.is_belong_observed_to_tutor import is_belong_observed_to_tutor


class UserAccessControlPermission(permissions.BasePermission):

    @check_role
    def has_permission(self, request, view):
        user = request.user

        req_user_id = int(get_param_from_request(request, view, 'user_id'))

        # if not user.is_authenticated:
        #     return False

        role_user = get_role(user)

        if role_user == Roles.ADMINISTRATOR.value:
            return True

        if user.pk == req_user_id:
            return True

        if role_user == Roles.TUTOR.value:
            return is_belong_observed_to_tutor(user, req_user_id)

        # isNotAllowedTutor = (
        #         role_user == Roles.TUTOR.value and
        #         not Observed.objects.filter(tutor=user, user_id=req_user_id).exists()
        # )

        # if isNotAllowedTutor:
        #     return False

        return False
