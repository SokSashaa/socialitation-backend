from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch

from socialize_main.models import User, Observed


def get_observed_by_user_id(user_id):
    if user_id:
        try:
            user = (User.objects.prefetch_related(
                Prefetch('observed_user',
                         queryset=Observed.objects.all(),
                         to_attr='_prefetched_observed')
            )
                    .get(pk=user_id))


            if not hasattr(user, '_prefetched_observed') or not user._prefetched_observed:
                raise ObjectDoesNotExist(f"У пользователя {user_id} не найден observed")

            return user._prefetched_observed[0]

        except User.DoesNotExist:
            raise ObjectDoesNotExist(f"Пользователь с ID {user_id} не найден")

    return None