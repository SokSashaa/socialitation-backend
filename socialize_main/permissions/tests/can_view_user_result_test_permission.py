from rest_framework.permissions import BasePermission

from socialize_main.constants.roles import Roles
from socialize_main.decorators.check_role import check_role
from socialize_main.models import TestObservered
from socialize_main.utils.get_param_from_request import get_param_from_request
from socialize_main.utils.get_role import get_role
from socialize_main.utils.is_belong_observed_to_tutor import is_belong_observed_to_tutor


class CanViewUserResultTestPermission(BasePermission):

    @check_role
    def has_permission(self, request, view):
        user = request.user

        role = get_role(user)

        if role == Roles.ADMINISTRATOR.value:
            return True

        req_user_id = get_param_from_request(request,view,'user_id')

        req_test_id = get_param_from_request(request,view,'test_id')


        if not req_user_id or not req_test_id:
            return False

        if role == Roles.TUTOR.value:
            return is_belong_observed_to_tutor(user, req_user_id)

        if role == Roles.OBSERVED.value:
            return TestObservered.objects.filter(test_id=req_test_id, observed__user_id=req_user_id).exists()

        return False
