from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import action

from socialize_main.models import User
from socialize_main.serializers.users import UsersSerializer


class UsersView(viewsets.ReadOnlyModelViewSet):
    serializer_class = UsersSerializer

    def get_queryset(self):
        queryset = User.objects.all()
        return queryset

    @action(detail=False, methods=['GET'])
    def me(self, request):
        return JsonResponse({"success": True, "result": UsersSerializer(request.user).data})
