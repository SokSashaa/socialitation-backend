from socialize_main.constants.roles import Roles
from socialize_main.models import Tutor, Administrator, User, Observed
from socialize_main.utils.search_role import search_role


def process_user_roles(user, serializer):
    #получаем объект роли и название роли
    old_role_obj, old_role_name = search_role(user)

    # Проверка на существование роли и определенных полей
    has_required_keys = (
            serializer.validated_data.get('role', False) and
            'code' in serializer.validated_data['role'] and
            'tutor_id' in serializer.validated_data['role']
    )

    if has_required_keys:
        role_code = serializer.validated_data['role']['code']

        # определяем новую роль пользователя
        #Объект не будет создан, если уже есть в БД
        if role_code == Roles.TUTOR.value:
            Tutor.objects.get_or_create(user=user)
        elif role_code == Roles.ADMINISTRATOR.value:
            Administrator.objects.get_or_create(user=user)
        elif role_code == Roles.OBSERVED.value:
            tutor_id = serializer.validated_data['role']['tutor_id']

            tutor = User.objects.get(id=tutor_id)

            defaults = {
                'tutor': tutor,
                'address': serializer.validated_data['address'],
            }

            Observed.objects.update_or_create(user=user, defaults=defaults)

    if (
            not old_role_name == Roles.UNROLED.value
            and has_required_keys
            and serializer.validated_data['role']['code'] != old_role_name
    ):
        # удаляем старую роль пользователя
        old_role_obj.delete()