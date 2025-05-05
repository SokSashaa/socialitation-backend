from socialize_main.constants.roles import Roles
from socialize_main.models import Tutor, Administrator, Observed


def search_role(user):
    if hasattr(user, '_cached_role'):
        return user._cached_role_obj, user._cached_role

    roles = [
        (Roles.TUTOR.value, Tutor),
        (Roles.OBSERVED.value, Observed),
        (Roles.ADMINISTRATOR.value, Administrator),
    ]

    for role_name, model in roles:
        try:
            role_obj = model.objects.get(user=user)

            user._cached_role = role_name
            user._cached_role_obj = role_obj

            return role_obj, role_name
        except model.DoesNotExist:
            pass

    return None, Roles.UNROLED.value