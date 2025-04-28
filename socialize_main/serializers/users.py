from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from socialize_main.constants.roles import Roles
from socialize_main.models import Tutor, User, GamesObserved, TestObservered, Observed, Administrator
from socialize_main.serializers.games import SingleGameSerializer
from socialize_main.serializers.organizations import CompactOrganizationSerializer
from socialize_main.serializers.tests import TestObsSerializer


class UsersSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField(method_name='get_role')
    address = serializers.SerializerMethodField(method_name='get_address')
    organization = CompactOrganizationSerializer()

    def get_address(self, obj):
        if obj.observed_user.count() > 0:
            return obj.observed_user.first().address
        return  ''

    def get_role(self, obj):
        if hasattr(obj, 'role_annotated'):
            return obj.role_annotated

            # Fallback для случая без аннотаций
        if getattr(obj, '_prefetched_tutor', None) or obj.tutor_user.exists():
            return Roles.TUTOR.value
        elif getattr(obj, '_prefetched_observed', None) or obj.observed_user.exists():
            return Roles.OBSERVED.value
        elif getattr(obj, '_prefetched_admin', None) or obj.administrator_user.exists():
            return Roles.ADMINISTRATOR.value
        return Roles.UNROLED.value

    # def get_role(self, obj):
    #     if obj.tutor_user.count() > 0:
    #         return Roles.TUTOR.value
    #     elif obj.observed_user.count() > 0:
    #         return Roles.OBSERVED.value
    #     elif obj.administrator_user.count() > 0:
    #         return Roles.ADMINISTRATOR.value
    #     else:
    #         return Roles.UNROLED.value

    # def get_organization(self,obj):
    #     if obj.organization:
    #         return {
    #             'id': obj.organization.id,
    #             'name': obj.organization.name
    #         }
    #     return None

    class Meta:
        model = User
        fields = (
            'id', 'login', 'email', 'second_name', 'name', 'patronymic', 'role', 'photo', 'birthday', 'phone_number',
            'organization', 'address')
        read_only_fields = ['id']


class ObservedSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField(method_name='get_role')
    tests = serializers.SerializerMethodField(method_name='get_tests')
    games = serializers.SerializerMethodField(method_name='get_games')
    address = serializers.SerializerMethodField(method_name='get_address')

    def get_address(self, obj):
        return obj.observed_user.first().address

    def get_games(self, obj):
        games = GamesObserved.objects.filter(observed=obj.observed_user.first())
        return SingleGameSerializer(games, many=True).data

    def get_tests(self, obj):
        tests = TestObservered.objects.filter(observed=obj.observed_user.first())
        return TestObsSerializer(tests.all(), many=True).data

    def get_role(self, obj):
        return "observed"

    class Meta:
        model = User
        fields = ('id', 'email', 'second_name', 'name', 'patronymic', 'role', 'games', 'tests', 'address')
        read_only_fields = ['id']


class ChangeUserInfoSerializer(serializers.Serializer):
    name = serializers.CharField(help_text='Имя юзера')
    second_name = serializers.CharField(help_text='Фамилия юзера')
    patronymic = serializers.CharField(help_text='Отчество юзера', required=False, allow_null=True, allow_blank=True)
    email = serializers.CharField(help_text='Почта юзера')
    birthday = serializers.DateField()
    photo = serializers.CharField(help_text='Ссылка на фото', required=False, allow_null=True, allow_blank=True)
    role = serializers.JSONField(help_text='Роль', required=False)
    organization = serializers.IntegerField(help_text='Организация', required=False)
    phone_number = serializers.CharField(help_text='Телефон')
    address = serializers.CharField(help_text='Адрес', required=False, allow_blank=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class ChangePasswordAdminSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True)


class UserRegSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    birthday = serializers.DateField()
    role = serializers.JSONField(default={})
    photo = serializers.CharField(allow_blank=True, allow_null=True)
    address = serializers.CharField(allow_blank=True)
    phone_number = serializers.CharField()

    class Meta:
        model = User
        fields = (
            'login', 'email', 'name', 'second_name', 'patronymic', 'password', 'birthday', 'role', 'photo',
            'phone_number',
            'organization', 'address')

    @transaction.atomic
    def create(self, validated_data):
        try:
            user = User.objects.get(Q(email=validated_data['email']) | Q(login=validated_data['login']))
            return None, False
        except User.DoesNotExist:
            user, created = User.objects.get_or_create(
                email=validated_data['email'],
                login=validated_data['login'],
                defaults={
                    'name': validated_data.get('name', ''),
                    'second_name': validated_data.get('second_name', ''),
                    'patronymic': validated_data.get('patronymic', ''),
                    'organization': validated_data.get('organization', 1),
                    'birthday': validated_data.get('birthday', '1990-01-01'),
                    'phone_number': validated_data['phone_number'],
                }
            )
            if created:
                user.set_password(validated_data['password'])
                user.save()
                if validated_data['role'].get('code', '') == Roles.TUTOR.value:
                    tutor = Tutor.objects.get_or_create(
                        user=user),
                elif validated_data['role'].get('code', '') == Roles.OBSERVED.value:
                    observed = Observed.objects.get_or_create(user=user, tutor=User.objects.get(
                        pk=validated_data['role']['tutor_id']),
                                                              address=validated_data['address'])
                elif validated_data['role'].get('code', '') == Roles.ADMINISTRATOR.value:
                    administrator = Administrator.objects.get_or_create(
                        user=user)
            return user, created


class TutorsSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(source='user.name')
    second_name = serializers.CharField(source='user.second_name')
    patronymic = serializers.CharField(source='user.patronymic')


class AllTutorsSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    second_name = serializers.CharField()
    patronymic = serializers.CharField()

    class Meta:
        model = User
        fields = ('id', 'name', 'second_name', 'patronymic')
        read_only_fields = ['id']


class AppointObservedSerializer(serializers.Serializer):
    link = serializers.ListField(help_text='Список юзеров для привязки', child=serializers.IntegerField())
    tutor_id = serializers.IntegerField(help_text='Тьютор для действий')
