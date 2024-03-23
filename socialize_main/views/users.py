from rest_framework import viewsets

from socialize_main.models import User
from socialize_main.serializers.users import UsersSerializer


class UsersView(viewsets.ReadOnlyModelViewSet):
    serializer_class = UsersSerializer

    def get_queryset(self):
        queryset = User.objects.all()
        return queryset