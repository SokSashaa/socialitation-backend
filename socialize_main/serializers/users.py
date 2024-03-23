from django.db.migrations import serializer

from socialize_main.models import User


class UsersSerializer(serializer.ModelFieldSerializer):

    class Meta:
        model = User
        fields = ('__all__')