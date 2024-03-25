from rest_framework import serializers

from socialize_main.models import User


class UsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'
        read_only_fields = ['id']