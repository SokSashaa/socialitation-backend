import os
import shutil
import zipfile
from http.client import error

from django import forms
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination

from socialize_main.constants.file_const import ZIP_FILE_FORMAT
from socialize_main.constants.roles import Roles
from socialize_main.models import User, Games, GamesObserved
from socialize_main.permissions.role_permission import RolePermission
from socialize_main.permissions.user_access_control_permission import UserAccessControlPermission
from socialize_main.serializers.games import GameSerializer, AppointGameSerializer, CreateGameSerializer, \
    UpdateGameSerializer, GetUserGamesSerializer
from socialize_main.utils.deleteImage import delete_image
from socialize_main.utils.get_observed_by_user_id import get_observed_by_user_id
from socialize_main.utils.get_random_string_name import generate_random_name
from socialize_main.utils.savingImage import saving_image


@xframe_options_sameorigin
def game_view(request, game_name):
    template_path = f'games/{game_name}/index.html'  # Предполагаем, что главный файл HTML называется index.html
    return render(request, template_path, {'game_name': game_name})


class UploadArchiveForm(forms.Form):
    archive_file = forms.FileField()
    game_title = forms.CharField()
    game_description = forms.CharField()
    game_icon = forms.FileField()


class GamesView(viewsets.ReadOnlyModelViewSet):
    serializer_class = GameSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering = ['-pk', 'name']
    ordering_fields = ['name', 'id']
    search_fields = ['name']

    def get_permissions(self):
        if self.action in ['get_obs_games']:
            return [UserAccessControlPermission()]
        return [RolePermission(Roles.ADMINISTRATOR.value)]

    def get_queryset(self):
        queryset = Games.objects.all()

        return queryset

    def _paginate_queryset(self, queryset, request, serializer_class):
        paginator = LimitOffsetPagination()
        pagination_queryset = paginator.paginate_queryset(queryset, request)

        serializer = serializer_class(pagination_queryset, many=True)

        return paginator.get_paginated_response(serializer.data)

    @action(methods=['POST'], detail=False)
    def upload(self, request):
        serializer = CreateGameSerializer(data=request.data)
        image_str = None
        archive_path = None
        directory_name = None
        isError = False
        if not serializer.is_valid():
            return JsonResponse({'success': False, 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            archive_file = serializer.validated_data['archive_file']
            game_name = serializer.validated_data['name']
            game_description = serializer.validated_data['description']

            fs = FileSystemStorage(location='templates/games/')

            directory_name = generate_random_name()

            filename = fs.save(f"{directory_name}{ZIP_FILE_FORMAT}", archive_file)

            # Распаковка архива
            archive_path = os.path.join(fs.location, filename)

            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(os.path.join(fs.location, directory_name))

            image_str = saving_image(serializer, 'icon')
            # Формирование ссылки на игру
            game_link = request.build_absolute_uri(reverse('game_view', kwargs={'game_name': directory_name}))

            # Создание объекта Games
            game = Games.objects.create(name=game_name,
                                        description=game_description,
                                        link=game_link,
                                        directory_name=directory_name,
                                        icon=image_str)

            return JsonResponse({'success': True, 'result': GameSerializer(game).data}, status=status.HTTP_200_OK)

        except zipfile.BadZipFile:
            return JsonResponse({'success': False, 'error': 'Архив поврежден или некорректен'},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            isError = True
            return JsonResponse({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            if isError:
                if image_str:
                    delete_image(image_str)

                game_directory = os.path.join(settings.TEMPLATES[0]['DIRS'][0], 'games', directory_name)
                if directory_name and os.path.exists(game_directory):
                    shutil.rmtree(game_directory)


            if archive_path and os.path.exists(archive_path):
                try:
                    os.remove(archive_path)
                except Exception as e:
                    print(f"Ошибка при удалении архива: {e}")

    @action(methods=['POST'], detail=True)
    def update_game(self, request, pk):
        serializer = UpdateGameSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({'success': False, 'errors': serializer.errors})
        try:
            game = Games.objects.get(pk=pk)
            game.name = serializer.validated_data['name']
            game.description = serializer.validated_data['description']

            image_str = saving_image(serializer, 'icon')

            if image_str:
                delete_image(game.icon)
                game.icon = image_str

            game.save()
            return JsonResponse({'success': True, 'result': GameSerializer(game).data}, status=status.HTTP_200_OK)
        except Games.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Игра не найдена'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST'], detail=False)
    def appoint_game(self, request):
        serializer = AppointGameSerializer(data=request.data)

        if not serializer.is_valid():
            return JsonResponse({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            game_id = serializer.validated_data['game_id']

            game = Games.objects.get(pk=game_id)

            for link_user in serializer.validated_data['link']:
                observed = get_observed_by_user_id(link_user)

                _, created = GamesObserved.objects.get_or_create(game=game,
                                                                 observed=observed)

            for unlink_user in serializer.validated_data['unlink']:
                try:
                    observed = get_observed_by_user_id(unlink_user)

                    GamesObserved.objects.get(game=game, observed=observed).delete()
                except GamesObserved.DoesNotExist:
                    pass

            return JsonResponse({'success': True}, status=status.HTTP_200_OK)

        except Games.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Игра не найдена']}, status=status.HTTP_400_BAD_REQUEST)
        except Games.MultipleObjectsReturned:
            return JsonResponse({'success': False, 'errors': ['Найдено несколько игр']},
                                status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            return JsonResponse({'success': False, 'errors': [str(e)]},
                                status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['GET'], detail=False)
    def get_obs_games(self, request):
        data = request.query_params

        serializer = GetUserGamesSerializer(data=data)

        if not serializer.is_valid():
            return JsonResponse({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id = serializer.validated_data.get('user_id',False)
            observed = get_observed_by_user_id(user_id)

            games = list(
                GamesObserved.objects.filter(observed=observed).values_list('game__pk', flat=True))

            search_name = serializer.validated_data.get('search', False)

            if search_name:
                g_games = Games.objects.filter(pk__in=games, name__icontains=search_name)
            else:
                g_games = Games.objects.filter(pk__in=games)

            return self._paginate_queryset(g_games, request, GameSerializer)
            # return JsonResponse({'success': True, 'results': GameSerializer(g_games, many=True).data},
            #                     status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Пользователь не найден']},
                                status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            return JsonResponse({'success': False, 'errors': [str(e)]},
                                status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST', 'DELETE'], detail=True)
    def delete_game(self, request, pk):
        try:
            game = Games.objects.get(pk=pk)
            game_directory = os.path.join(settings.TEMPLATES[0]['DIRS'][0], 'games', game.directory_name)
            game.delete()

            if game.icon:
                delete_image(game.icon)

            if os.path.exists(game_directory):
                shutil.rmtree(game_directory)

            return JsonResponse({'success': True, 'message': 'Игра успешно удалена'}, status=status.HTTP_200_OK)
        except Games.DoesNotExist:
            return JsonResponse({'success': False, 'errors': 'Игра не найдена'}, status=status.HTTP_400_BAD_REQUEST)
