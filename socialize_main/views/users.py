import time

from django.db import IntegrityError, connection
from django.db.models import When, Case, Value, CharField, Prefetch
from django.http import JsonResponse
from django_filters import rest_framework as dj_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated

from socialize_main.constants.roles import Roles
from socialize_main.models import User, Observed, Tutor, Administrator, Organization
from socialize_main.permissions.user_access_control_permission import UserAccessControlPermission
from socialize_main.permissions.role_permission import RolePermission
from socialize_main.serializers.users import UserRegSerializer, UsersSerializer, ObservedSerializer, \
    ChangeUserInfoSerializer, ChangePasswordSerializer, AppointObservedSerializer, \
    ChangePasswordAdminSerializer, AllTutorsSerializer
from socialize_main.utils.deleteImage import delete_image
from socialize_main.utils.savingImage import saving_image
from socialize_main.utils.search_role import search_role
from socialize_main.utils.users.get_integrity_error_user import get_integrity_error_user
from socialize_main.utils.users.process_user_roles import process_user_roles


def filter_by_role(queryset, name, value):
    if queryset.objects.filter(tutor_user__isnull=False) and value == Roles.TUTOR.value:
        queryset = queryset.objects.filter(tutor_user__isnull=False)
    elif queryset.objects.filter(observed_user__isnull=False) and value == Roles.OBSERVED.value:
        queryset = queryset.objects.filter(observed_user__isnull=False)
    elif queryset.objects.filter(administrator_user__isnull=False) and value == Roles.ADMINISTRATOR.value:
        queryset = queryset.objects.filter(administrator_user__isnull=False)
    else:
        queryset = queryset.objects.none()
    return queryset


class UserFilter(dj_filters.FilterSet):
    role = dj_filters.CharFilter(method=filter_by_role, label='Роль')


class UsersView(viewsets.ReadOnlyModelViewSet):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    serializer_class = UsersSerializer
    filterset_fields = []
    ordering = ['-pk', 'name']  ## по умолчанию
    ordering_fields = ['pk', 'name', 'organization']  ##по каким полям можно сортировать
    search_fields = ['name', 'second_name', 'login', 'phone_number', 'organization__name']

    # Для действий, которые должны быть доступны без аутентификации:
    def get_permissions(self):
        if self.action in ['change_password', 'me']:
            return [IsAuthenticated()]
        if self.action in ['list', 'delete_user', 'get_tutors', 'register_user']:  ##list - это /users/
            return [RolePermission([Roles.ADMINISTRATOR.value])]
        if self.action in ['retrieve','change_user_info', 'get_tutor_by_observed', 'delete_avatar']:
            return [UserAccessControlPermission()]
        return [RolePermission([Roles.ADMINISTRATOR.value, Roles.TUTOR.value])]

    def get_queryset(self):
        queryset = User.objects.select_related('organization').prefetch_related(
            Prefetch('tutor_user', queryset=Tutor.objects.only('id', 'user_id'), to_attr='_prefetched_tutor'),
            Prefetch('observed_user',
                     queryset=Observed.objects.order_by('id').only('id', 'user_id', 'tutor_id', 'address'),
                     to_attr='_prefetched_observed'),
            Prefetch('administrator_user',
                     queryset=Administrator.objects.only('id', 'user_id'),
                     to_attr='_prefetched_admin')
        ).annotate(
            role_annotated=Case(
                When(tutor_user__isnull=False, then=Value(Roles.TUTOR.value)),
                When(observed_user__isnull=False, then=Value(Roles.OBSERVED.value)),
                When(administrator_user__isnull=False, then=Value(Roles.ADMINISTRATOR.value)),
                default=Value(Roles.UNROLED.value),
                output_field=CharField()
            )
        )

        return queryset

    @action(detail=True, methods=['DELETE'])
    def delete_user(self, request, pk):
        try:
            user = User.objects.get(pk=pk)

            if user.photo:
                delete_image(user.photo)

            user.delete()
            return JsonResponse({'success': True, 'result': 'Пользователь удален'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['GET'])
    def me(self, request):
        return JsonResponse({"success": True, "result": UsersSerializer(request.user).data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'])
    def get_observeds(self, request):
        data = request.query_params
        if data.get('text', False):
            try:
                first_pos = data['text'].split(' ')[0]
                users = User.objects.filter(second_name__icontains=first_pos) | User.objects.filter(
                    name__icontains=first_pos)
            except IndexError:
                users = User.objects.none()
            try:
                second_pos = data['text'].split(' ')[1]
                users = users | User.objects.filter(second_name__icontains=second_pos) | User.objects.filter(
                    name__icontains=second_pos)
            except IndexError:
                pass
        else:
            users = User.objects.filter(observed_user__isnull=False)
        return JsonResponse({'success': True, 'result': ObservedSerializer(users, many=True).data},
                            status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'])
    def get_observeds_by_tutor(self, request, pk):
        try:
            observeds = list(
                Observed.objects.filter(tutor_id=pk).values_list('user__pk', flat=True))
            users = User.objects.filter(pk__in=observeds)
            return JsonResponse({'success': True, 'result': ObservedSerializer(users, many=True).data},
                                status=status.HTTP_200_OK)
        except Tutor.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Тьютор не найден']}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Неверный параметр'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'success': False, 'error': e.__str__()}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'])
    def change_user_info(self, request, pk):
        serializer = ChangeUserInfoSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({'success': False, 'errors': serializer.errors})
        try:
            user = User.objects.get(pk=pk)

            user_fields = ['name', 'second_name', 'patronymic', 'email', 'birthday', 'phone_number']

            for field in user_fields:
                setattr(user, field, serializer.validated_data[field])

            user_organization = serializer.validated_data.get('organization', False)

            if user_organization and not user_organization == user.organization: ##TODO: Проверить условие
                organization_id = serializer.validated_data['organization']
                user.organization = Organization.objects.get(id=organization_id)

            # Процесс смены роли
            process_user_roles(user, serializer)

            # Проверка и сохранение изображения
            image_url = saving_image(serializer, 'photo')

            if image_url:
                delete_image(user.photo)
                user.photo = image_url

            user.save()

            return JsonResponse({'success': True, 'result': UsersSerializer(user).data}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'errors': 'Такого пользователя не найдено'},
                                status=status.HTTP_400_BAD_REQUEST)
        except Organization.DoesNotExist:
            return JsonResponse({'success': False, 'errors': 'Такая организация не найдена'},
                                status=status.HTTP_404_NOT_FOUND)
        except Tutor.DoesNotExist:
            return JsonResponse({'success': False, 'errors': 'Тьютор не найден'},
                                status=status.HTTP_404_NOT_FOUND)
        except KeyError as e:
            return JsonResponse({
                'success': False,
                'error': f'Не найдено обязательное поле: {e}'
            }, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            return JsonResponse({'success': False, "error": get_integrity_error_user(e)},
                                status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        user = request.user
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            if not user.check_password(serializer.validated_data['old_password']):
                return JsonResponse({'success': False, 'errors': ['Неправильный старый пароль']})
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return JsonResponse({'success': True, 'result': UsersSerializer(user).data}, status=status.HTTP_200_OK)
        return JsonResponse({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def change_password_user(self, request, pk):
        user = User.objects.get(pk=pk)
        if user:
            serializer = ChangePasswordAdminSerializer(data=request.data)
            if serializer.is_valid():
                _, role_user = search_role(user)
                if not role_user == Roles.ADMINISTRATOR.value:
                    user.set_password(serializer.validated_data['new_password'])
                    user.save()
                    return JsonResponse({'success': True, 'result': UsersSerializer(user).data},
                                        status=status.HTTP_200_OK)
                else:
                    return JsonResponse({'success': False, 'errors': 'Запрет на смену пароля администратору'})
            return JsonResponse({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return JsonResponse({'success': False, 'errors': 'Пользователь не найден'},
                                status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['POST'])
    def register_user(self, request):
        serializer = UserRegSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user, created = serializer.save()
                if created:
                    image_str = saving_image(serializer, 'photo')

                    user.photo = image_str

                    user.save()

                    return JsonResponse({'success': True, 'result': UsersSerializer(user).data},
                                        status=status.HTTP_200_OK)
                else:
                    return JsonResponse(
                        {'success': False, 'errors': 'Пользователь с таким логином или почтой уже существует'},
                        status=status.HTTP_400_BAD_REQUEST)
            except IntegrityError as e:
                return JsonResponse({'success': False, "errors": get_integrity_error_user(e)},
                                    status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['GET'], detail=False)
    def get_tutors(self, request):
        tutors = User.objects.exclude(id__in=Observed.objects.values_list('user_id', flat=True))
        return JsonResponse({'success': True, 'result': AllTutorsSerializer(tutors, many=True).data})

    @action(methods=['GET'], detail=True)
    def get_tutor_by_observed(self, request, pk):
        try:
            tutor_id = Observed.objects.get(user_id=pk).tutor_id
            user = User.objects.get(pk=tutor_id)
            return JsonResponse({'success': True, 'result': UsersSerializer(user).data})
        except Observed.DoesNotExist:
            return JsonResponse({'success': False, 'result': 'Наблюдаемый не найден'},
                                status=status.HTTP_404_NOT_FOUND)

    @action(methods=['POST'], detail=False)
    def appoint_observed(self, request):
        serializer = AppointObservedSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({'success': False, 'errors': serializer.errors})
        try:
            tutor = Tutor.objects.get(pk=serializer.validated_data['tutor_id'])
            response = ''
            for link_user in serializer.validated_data['link']:
                user = User.objects.get(pk=link_user)
                us_obs = user.observed_user.first()
                us_obs.tutor = tutor
                us_obs.save()
            if not response:
                return JsonResponse({'success': True}, status=status.HTTP_200_OK)
            else:
                return JsonResponse({'success': True, 'message': f'Пользователям: {response} тьютор уже назначен'},
                                    status=status.HTTP_400_BAD_REQUEST)
        except Tutor.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Тьютор не найден']}, status=status.HTTP_400_BAD_REQUEST)
        except Tutor.MultipleObjectsReturned:
            return JsonResponse({'success': False, 'errors': ['Найдено несколько тьюторов']},
                                status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST'], detail=True)
    def delete_avatar(self, request, pk):
        try:
            user = User.objects.get(pk=pk)

            delete_image(user.photo)

            user.photo = None

            user.save()

            return JsonResponse({'success': True, 'result': UsersSerializer(user).data}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'errors': 'Пользователь не найден'},
                                status=status.HTTP_400_BAD_REQUEST)
