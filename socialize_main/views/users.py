from django.db import IntegrityError
from django.http import JsonResponse
from django_filters import rest_framework as dj_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action

from socialize_main.models import User, Observed, Tutor, Administrator, Organization
from socialize_main.serializers.users import UserRegSerializer, UsersSerializer, ObservedSerializer, \
    ChangeUserInfoSerializer, ChangePasswordSerializer, AppointObservedSerializer, \
    ChangePasswordAdminSerializer, AllTutorsSerializer
from socialize_main.utils.deleteImage import delete_image
from socialize_main.utils.savingImage import saving_image


def search_role(user):
    roles = [
        ('tutor', Tutor),
        ('observed', Observed),
        ('administrator', Administrator),
    ]

    for old_role_name, model in roles:
        try:
            old_role_obj = model.objects.get(user=user)
            return old_role_obj, old_role_name
        except model.DoesNotExist:
            pass

    return None, 'no role'


def filter_by_role(queryset, name, value):
    if queryset.objects.filter(tutor_user__isnull=False) and value == 'tutor':
        queryset = queryset.objects.filter(tutor_user__isnull=False)
    elif queryset.objects.filter(observed_user__isnull=False) and value == 'observed':
        queryset = queryset.objects.filter(observed_user__isnull=False)
    elif queryset.objects.filter(administrator_user__isnull=False) and value == 'administrator':
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
    ordering = ['-pk', 'name']
    search_fields = ['name']

    def get_queryset(self):
        queryset = User.objects.all()
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

    @action(detail=False, methods=['GET'])  # TODO ЗАЛИТЬ
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
            tutor = User.objects.get(pk=pk)
            observeds = list(
                Observed.objects.filter(tutor=tutor).values_list('user__pk', flat=True))  # TODO: Тут было исправлено
            users = User.objects.filter(pk__in=observeds)
            return JsonResponse({'success': True, 'result': ObservedSerializer(users, many=True).data},
                                status=status.HTTP_200_OK)
        except Tutor.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Тьютор не найден']}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Неверный параметр'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'success': False, 'error': e}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'])
    def change_user_info(self, request, pk):
        serializer = ChangeUserInfoSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({'success': False, 'errors': serializer.errors})
        try:
            user = User.objects.get(pk=pk)
            user.name = serializer.validated_data['name']
            user.second_name = serializer.validated_data['second_name']
            user.patronymic = serializer.validated_data['patronymic']
            user.email = serializer.validated_data['email']
            user.date_of_birth = serializer.validated_data['birthday']
            user.phone_number = serializer.validated_data['phone_number']
            old_role_obj, old_role_name = search_role(user)

            if serializer.validated_data.get('organization', False):
                user.organization = Organization.objects.get(id=serializer.validated_data['organization'])

            #Проверка и сохранение изображения
            image_url = saving_image(serializer, 'photo')

            if image_url:
                delete_image(user.photo)
                user.photo = image_url

                # Проверка на существование роли и определенных полей
            has_required_keys = (
                    serializer.validated_data.get('role', False) and
                    'code' in serializer.validated_data['role'] and
                    'tutor_id' in serializer.validated_data['role']
            )

            if (
                    has_required_keys
                    # and serializer.validated_data['role']['code'] != old_role_name
            ):
                role_code = serializer.validated_data['role']['code']
                # определяем роль пользователя
                if role_code == 'tutor':
                    Tutor.objects.get_or_create(user=user)
                elif role_code == 'administrator':
                    Administrator.objects.get_or_create(user=user)
                elif role_code == 'observed':
                    tutor = User.objects.get(id=serializer.validated_data['role']['tutor_id'])
                    defaults = {
                        'tutor': tutor,
                        'address': serializer.validated_data['address'],
                    }
                    Observed.objects.update_or_create(user=user, defaults=defaults)

            if (
                    not old_role_name == 'no role'
                    and has_required_keys
                    and serializer.validated_data['role']['code'] != old_role_name
            ):
                # удаляем старую роль пользователя
                old_role_obj.delete()
            user.save()
            return JsonResponse({'success': True, 'result': UsersSerializer(user).data}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Такого пользователя не найдено']},
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
            return JsonResponse({"error": "Указанная почта уже занята."}, status=status.HTTP_400_BAD_REQUEST)

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
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                return JsonResponse({'success': True, 'result': UsersSerializer(user).data},
                                    status=status.HTTP_200_OK)
            return JsonResponse({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['POST'])
    def register_user(self, request):
        serializer = UserRegSerializer(data=request.data)
        if serializer.is_valid():
            user, created = serializer.save()
            if created:
                image_str = saving_image(serializer, 'photo')

                user.photo = image_str

                user.save()

                return JsonResponse({'success': True, 'result': UsersSerializer(user).data}, status=status.HTTP_200_OK)
            else:
                return JsonResponse(
                    {'success': False, 'errors': ['Пользователь с таким логином или почтой уже существует']},
                    status=status.HTTP_400_BAD_REQUEST)
        return JsonResponse({'success': False, 'errors': serializer.errors})

    @action(methods=['GET'], detail=False)
    def get_tutors(self, request):
        # tutors = Tutor.objects.all() #TODO: Тут было исправлено
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
