from django.urls import path, re_path, include

from rest_framework.routers import DefaultRouter

from socialize_main.views.tests import TestsView
from socialize_main.views.users import UsersView
from socialize_main.views import games
from socialize_main.views.games import GamesView

router = DefaultRouter()

router.register(r'users', UsersView, basename='users')
router.register(r'tests', TestsView, basename='tests')
router.register(r'games_list', GamesView, basename='games')

urlpatterns = [
    path('upload/', games.upload_archive, name='upload_archive'),
    path('games/', games.games_list, name='games_list'),
    path('game/<str:game_name>/', games.game_view, name='game_view'),
]

urlpatterns += router.urls
