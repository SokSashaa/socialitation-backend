import shutil
import time

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from django.shortcuts import render
from django import forms
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render, redirect
import os
import zipfile
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render, redirect
from django import forms
import os
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework import viewsets, filters, status

from socialize_main.models import User, Games, GamesObserved, Tutor
from socialize_main.serializers.games import GameSerializer, AppointGameSerializer


def game_view(request, game_name):
    template_path = f'games/{game_name}/index.html'  # Предполагаем, что главный файл HTML называется index.html
    return render(request, template_path, {'game_name': game_name})


class UploadArchiveForm(forms.Form):
    archive_file = forms.FileField()
    game_title = forms.CharField()
    game_description = forms.CharField()


def upload_archive(request):
    if request.method == 'POST':
        form = UploadArchiveForm(request.POST, request.FILES)
        if form.is_valid():
            archive_file = form.cleaned_data['archive_file']
            game_name = form.cleaned_data['game_title']
            game_description = form.cleaned_data['game_description']
            fs = FileSystemStorage(location='templates/games/')
            filename = fs.save(archive_file.name, archive_file)

            # Распаковка архива
            archive_path = os.path.join(fs.location, filename)
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(os.path.join(fs.location, game_name))

            # Удаление архива после распаковки
            os.remove(archive_path)

            # Создание объекта Games
            Games.objects.create(name=game_name, description=game_description, link=f'http://5.35.89.117:8084/game/{game_name}')
            return redirect('games_list')  # Редирект на список игр или другое представление
    else:
        form = UploadArchiveForm()
    return render(request, 'upload_archive.html', {'form': form})



def games_list(request):
    games_dir = os.path.join(settings.BASE_DIR, 'templates/games')
    games = [d for d in os.listdir(games_dir) if os.path.isdir(os.path.join(games_dir, d))]
    return render(request, 'games_list.html', {'games': games})

class GamesView(viewsets.ReadOnlyModelViewSet):
    serializer_class = GameSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering = ['-pk', 'name'] # TODO ЗАЛИТЬ
    search_fields = ['name']
    queryset = Games.objects.all()


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
                game_observed, created = GamesObserved.objects.get_or_create(game=game, observed=user.observed_user.first())
                if not created:
                    response += user.name + '. '
            for unlink_user in serializer.validated_data['unlink']:
                user = User.objects.get(pk=unlink_user)
                GamesObserved.objects.get(game=game, observed=user.observed_user.first()).delete()
            if not response:
                return JsonResponse({'success': True}, status=status.HTTP_200_OK)
            else:
                return JsonResponse({'success': True, 'message': f'Пользователям: {response} игра уже назначена'}, status=status.HTTP_400_BAD_REQUEST)
        except Games.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Игра не найдена']}, status=status.HTTP_400_BAD_REQUEST)
        except Games.MultipleObjectsReturned:
            return JsonResponse({'success': False, 'errors': ['Найдено несколько игр']}, status=status.HTTP_400_BAD_REQUEST)


    @action(methods=['GET'], detail=True)
    def get_obs_games(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
            games = list(GamesObserved.objects.filter(observed=user.observed_user.first()).values_list('game__pk', flat=True))
            g_games = Games.objects.filter(pk__in=games)
            return JsonResponse({'success': True, 'results': GameSerializer(g_games, many=True).data}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Пользователь не найден']}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST'], detail=True)
    def delete_game(self, request, pk):
        try:
            game = Games.objects.get(pk=pk)
            game_directory = os.path.join(settings.TEMPLATES[0]['DIRS'][0], 'games', game.name)
            game.delete()
            if os.path.exists(game_directory):
                shutil.rmtree(game_directory)
            return JsonResponse({'success': True, 'message': 'Game deleted successfully'}, status=status.HTTP_200_OK)
        except Games.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Игра не найдена']}, status=status.HTTP_400_BAD_REQUEST)


