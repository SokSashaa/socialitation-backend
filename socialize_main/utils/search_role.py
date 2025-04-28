from socialize_main.constants.roles import Roles
from socialize_main.models import Tutor, Administrator, Observed


def search_role(user):
    roles = [
        (Roles.TUTOR.value, Tutor),
        (Roles.OBSERVED.value, Observed),
        (Roles.ADMINISTRATOR.value, Administrator),
    ]

    for old_role_name, model in roles:
        try:
            old_role_obj = model.objects.get(user=user)
            return old_role_obj, old_role_name
        except model.DoesNotExist:
            pass

    return None, Roles.UNROLED.value