import os
import shutil
import zipfile

from django import forms
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from socialize_main.constants.file_const import ZIP_FILE_FORMAT
from socialize_main.constants.roles import Roles
from socialize_main.models import User, Games, GamesObserved
from socialize_main.permissions.role_permission import RolePermission
from socialize_main.serializers.games import GameSerializer, AppointGameSerializer, CreateGameSerializer, \
    UpdateGameSerializer
from socialize_main.utils.deleteImage import delete_image
from socialize_main.utils.randomName import random_name
from socialize_main.utils.savingImage import saving_image


def game_view(request, game_name):
    template_path = f'games/{game_name}/index.html'  # Предполагаем, что главный файл HTML называется index.html
    return render(request, template_path, {'game_name': game_name})


class UploadArchiveForm(forms.Form):
    archive_file = forms.FileField()
    game_title = forms.CharField()
    game_description = forms.CharField()
    game_icon = forms.FileField()


# @csrf_exempt  ##TODO убрать декоратор когда закончится тестирование
# def upload_archive(request):
#     if request.method == 'POST':
#         form = UploadArchiveForm(request.POST, request.FILES)
#         if form.is_valid():
#             archive_file = form.cleaned_data['archive_file']
#             game_name = form.cleaned_data['game_title'].strip().replace(' ', '_')
#             game_description = form.cleaned_data['game_description']
#             game_icon = form.cleaned_data['game_icon']
#             fs = FileSystemStorage(location='templates/games/')
#             archive_path = ''
#             directory_name = ''
#
#             try:
#                 if archive_file.size > 10 * 1024 * 1024:
#                     raise ValueError('ZIP файл больше 10 МБ')
#
#                 filename = fs.save(archive_file.name, archive_file)
#
#                 # Распаковка архива
#                 archive_path = os.path.join(fs.location, filename)  # обработку ошибок архива
#                 with zipfile.ZipFile(archive_path, 'r') as zip_ref:
#                     files_in_archive = zip_ref.namelist()
#                     if 'index.html' not in files_in_archive:
#                         raise ValueError('Отсутствует index.html файл')
#
#                     directory_name = f"{game_name}_{random_name()}"
#                     zip_ref.extractall(os.path.join(fs.location, directory_name))
#
#                 # Создание объекта Games
#                 Games.objects.create(name=game_name, description=game_description,
#                                      link=f'http://127.0.0.1:8000/api/game/{directory_name}',
#                                      directory_name=directory_name, icon=game_icon)  # TODO: исправить ссылку
#                 return redirect('games_list')  # Редирект на список игр или другое представление
#             except zipfile.BadZipFile:
#                 return JsonResponse({'success': False, 'error': 'Архив поврежден или некорректен'},
#                                     status=status.HTTP_400_BAD_REQUEST)
#             except Exception as e:
#                 return JsonResponse({'success': False, 'error': str(e)}, )
#             finally:
#                 if archive_path and os.path.exists(archive_path):
#                     try:
#                         os.remove(archive_path)
#                     except Exception as e:
#                         print(f"Ошибка при удалении архива: {e}")
#     else:
#         form = UploadArchiveForm()
#     return render(request, 'upload_archive.html', {'form': form})  # скорее всего выводить просто ошибку
#

# def games_list(request):
#     games_dir = os.path.join(settings.BASE_DIR, 'templates/games')
#     games = [d for d in os.listdir(games_dir) if os.path.isdir(os.path.join(games_dir, d))]
#     return render(request, 'games_list.html', {'games': games})


class GamesView(viewsets.ReadOnlyModelViewSet):
    serializer_class = GameSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering = ['-pk', 'name']  # TODO ЗАЛИТЬ
    search_fields = ['name']
    permission_classes = [IsAuthenticated]
    queryset = Games.objects.all()

    def get_permissions(self):
        if self.action in ['get_obs_games']:
            return [IsAuthenticated()]
        return [RolePermission(Roles.ADMINISTRATOR.value)]

    @action(methods=['POST'], detail=False)
    def upload(self, request):

        serializer = CreateGameSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({'success': False, 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            archive_file = serializer.validated_data['archive_file']
            game_name = serializer.validated_data['name'].strip().replace(' ', '_')
            game_description = serializer.validated_data['description']

            fs = FileSystemStorage(location='templates/games/')

            directory_name = f"{game_name}_{random_name()}"

            if archive_file.size > 10 * 1024 * 1024:
                raise ValueError('ZIP файл больше 10 МБ')

            filename = fs.save(f"{directory_name}{ZIP_FILE_FORMAT}", archive_file)

            # Распаковка архива
            archive_path = os.path.join(fs.location, filename)  # обработку ошибок архива

            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                files_in_archive = zip_ref.namelist()
                if 'index.html' not in files_in_archive:
                    raise ValueError('Отсутствует index.html файл')

                zip_ref.extractall(os.path.join(fs.location, directory_name))

            image_str = saving_image(serializer, 'icon')

            #Формирование ссылки на игру
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
            return JsonResponse({'success': False, 'error': str(e)}, )
        finally:
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
            game = Games.objects.get(pk=serializer.validated_data['game_id'])
            response = ''
            for link_user in serializer.validated_data['link']:
                user = User.objects.get(pk=link_user)
                game_observed, created = GamesObserved.objects.get_or_create(game=game,
                                                                             observed=user.observed_user.first())
                if not created:
                    response += user.name + '. '
            for unlink_user in serializer.validated_data['unlink']:
                user = User.objects.get(pk=unlink_user)
                GamesObserved.objects.get(game=game, observed=user.observed_user.first()).delete()
            if not response:
                return JsonResponse({'success': True}, status=status.HTTP_200_OK)
            else:
                return JsonResponse({'success': True, 'message': f'Пользователям: {response} игра уже назначена'},
                                    status=status.HTTP_400_BAD_REQUEST)
        except Games.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Игра не найдена']}, status=status.HTTP_400_BAD_REQUEST)
        except Games.MultipleObjectsReturned:
            return JsonResponse({'success': False, 'errors': ['Найдено несколько игр']},
                                status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['GET'], detail=True)
    def get_obs_games(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
            games = list(
                GamesObserved.objects.filter(observed=user.observed_user.first()).values_list('game__pk', flat=True))
            g_games = Games.objects.filter(pk__in=games)
            return JsonResponse({'success': True, 'results': GameSerializer(g_games, many=True).data},
                                status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Пользователь не найден']},
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
