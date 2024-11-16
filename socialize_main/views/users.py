import base64
import os
import random

from django.core.files.base import ContentFile
from django.http import JsonResponse
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as dj_filters

from SocializationProject import settings
from socialize_main.models import User, Observed, Tutor, Administrator, Organization
from socialize_main.serializers.users import UserRegSerializer, UsersSerializer, ObservedSerializer, \
    ChangeUserInfoSerializer, ChangePasswordSerializer, TutorsSerializer, AppointObservedSerializer


def search_role(user):
    old_role_obj = ''
    old_role_name = ''
    try:
        old_role_obj = Tutor.objects.get(user=user)
        old_role_name = 'tutor'
    except Tutor.DoesNotExist:
        try:
            old_role_obj = Observed.objects.get(user=user)
            old_role_name = 'observed'
        except Observed.DoesNotExist:
            old_role_obj = Administrator.objects.get(user=user)
            old_role_name = 'administrator'
    return old_role_obj, old_role_name


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
    ordering = ['-pk', 'name']  # TODO ЗАЛИТЬ
    search_fields = ['name']

    def get_queryset(self):
        queryset = User.objects.all()
        return queryset

    @action(detail=True, methods=['DELETE'])
    def delete_user(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
            image_name =  user.photo[user.photo.rfind('\\')+1:]
            image = os.path.join(settings.MEDIA_ROOT, 'uploaded_images', image_name)
            if os.path.isfile(image):
                os.remove(image)

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
        return JsonResponse({'success': True, 'results': ObservedSerializer(users, many=True).data},
                            status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'])
    def get_observeds_by_tutor(self, request, pk):
        try:
            tutor = User.objects.get(pk=pk)
            observeds = list(Observed.objects.filter(tutor=tutor.tutor_user.first()).values_list('user__pk', flat=True))
            users = User.objects.filter(pk__in=observeds)
            return JsonResponse({'success': True, 'results': ObservedSerializer(users, many=True).data},
                                status=status.HTTP_200_OK)
        except Tutor.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Тьютор не найден']}, status=status.HTTP_400_BAD_REQUEST)

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
            old_role_obj,old_role_name = search_role(user)
            if user.observed_user.count() > 0:
                obs = user.observed_user.first()
                obs.date_of_birth = serializer.validated_data['birthday']
                obs.save()
            if serializer.validated_data.get('photo', False):
                image_data = serializer.validated_data['photo']
                image_name = f"{random.randint(1, 10000)}_photo.png"  # уникальное имя для каждого пользователя
                image_path = os.path.join(settings.MEDIA_ROOT, 'uploaded_images', image_name)

                # Ensure the directory exists
                os.makedirs(os.path.dirname(image_path), exist_ok=True)

                # Декодируем изображение из base64
                try:
                    format, imgstr = image_data.split(';base64,')
                except ValueError:
                    return JsonResponse({'success': False, 'errors': ['Неправильный формат изображения']},
                                        status=status.HTTP_400_BAD_REQUEST)

                data = ContentFile(base64.b64decode(imgstr), name=image_name)

                # Сохраняем изображение
                with open(image_path, 'wb') as destination:
                    destination.write(data.read())

                # Формируем URL для сохраненного изображения
                image_url = os.path.join(settings.MEDIA_URL, 'uploaded_images', image_name)
                user.photo = image_url
            if serializer.validated_data['role'] and serializer.validated_data['role'] != old_role_name:
                print('заход')
                old_role_obj.delete()
                if serializer.validated_data['role'] == 'tutor':
                    Tutor.objects.get_or_create(user=user, organization=Organization.objects.first())
                elif serializer.validated_data['role'] == 'administrator':
                    Administrator.objects.create(user=user)
                elif serializer.validated_data['role'] == 'observed':
                    Observed.objects.get_or_create(user=user, tutor=Tutor.objects.get(
                        pk=serializer.validated_data['role']['tutor_id']),
                                                   organization=Organization.objects.first(), ##TODO здесь не первую запись, а то что укажут на фронте. Если что есть в сереализаторе
                                                   date_of_birth=serializer.validated_data['birthday'],
                                                   address='г. Москва')

            user.save()
            return JsonResponse({'success': True, 'result': UsersSerializer(user).data}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Такого пользователя не найдено']},
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

    @action(detail=False, methods=['POST'])
    def register_user(self, request):
        serializer = UserRegSerializer(data=request.data)
        if serializer.is_valid():
            user, created = serializer.save()
            if created:
                try:
                    if serializer.validated_data['photo']:
                        image_data = serializer.validated_data['photo']
                        image_name = f"{random.randint(1, 10000)}_photo.png"  # уникальное имя для каждого пользователя
                        image_path = os.path.join(settings.MEDIA_ROOT, 'uploaded_images', image_name)

                        # Ensure the directory exists
                        os.makedirs(os.path.dirname(image_path), exist_ok=True)

                        # Декодируем изображение из base64
                        try:
                            format, imgstr = image_data.split(';base64,')
                        except ValueError:
                            pass

                        data = ContentFile(base64.b64decode(imgstr), name=image_name)

                        # Сохраняем изображение
                        with open(image_path, 'wb') as destination:
                            destination.write(data.read())

                        # Формируем URL для сохраненного изображения
                        image_url = os.path.join(settings.MEDIA_URL, 'uploaded_images', image_name)
                        user.photo = image_url
                    else:
                        user.photo = ''
                except KeyError:
                    pass
                user.save()
                return JsonResponse({'success': True, 'result': UsersSerializer(user).data}, status=status.HTTP_200_OK)
            else:
                return JsonResponse(
                    {'success': False, 'errors': ['Пользователь с таким логином или почтой уже существует']},
                    status=status.HTTP_400_BAD_REQUEST)
        return JsonResponse({'success': False, 'errors': serializer.errors})

    @action(methods=['GET'], detail=False)
    def get_tutors(self, request):
        tutors = Tutor.objects.all()
        return JsonResponse({'success': True, 'results': TutorsSerializer(tutors, many=True).data})

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
