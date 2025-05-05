from socialize_main.constants.roles import Roles
from socialize_main.models import Observed
from socialize_main.utils.get_role import get_role


def is_belong_observed_to_tutor(user, observed_id):
    role = get_role(user)

    result = (
            role == Roles.TUTOR.value and
            Observed.objects.filter(tutor=user, user__id=observed_id).exists()
    )

    return result
