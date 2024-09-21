from rest_framework import serializers

from socialize_main.models import Games

class GameSerializer(serializers.ModelSerializer):

    class Meta:
        model = Games
        fields = ('id','name', 'description', 'link')
        read_only_fields = ['id']


class SingleGameSerializer(serializers.Serializer):
    game = GameSerializer()


class AppointGameSerializer(serializers.Serializer):
    link = serializers.ListField(help_text='Список юзеров для привязки', child=serializers.IntegerField())
    unlink = serializers.ListField(help_text='Список юзеров для отвязки', child=serializers.IntegerField())
    game_id = serializers.IntegerField(help_text='Игра для действий')
