from django.urls import path, re_path, include

from rest_framework.routers import DefaultRouter

from socialize_main.views.users import UsersView

router = DefaultRouter()

router.register(r'users', UsersView, basename='users')

urlpatterns = router.urls
