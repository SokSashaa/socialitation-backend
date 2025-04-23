from rest_framework import serializers

from socialize_main.models import Games

class BaseGameSerializer(serializers.Serializer):
    name = serializers.CharField(help_text='Название игры')
    description = serializers.CharField(help_text='Описание игры')
    icon = serializers.CharField(help_text='Иконка игры', required=False, allow_blank=True, default='')

class GameSerializer(serializers.ModelSerializer):

    class Meta:
        model = Games
        fields = ('id','name', 'description', 'link', 'icon')
        read_only_fields = ['id']


class CreateGameSerializer(BaseGameSerializer):
    archive_file = serializers.FileField(help_text='Архив игры')

class UpdateGameSerializer(BaseGameSerializer):
    pass

class SingleGameSerializer(serializers.Serializer):
    game = GameSerializer()

class AppointGameSerializer(serializers.Serializer):
    link = serializers.ListField(help_text='Список юзеров для привязки', child=serializers.IntegerField())
    unlink = serializers.ListField(help_text='Список юзеров для отвязки', child=serializers.IntegerField())
    game_id = serializers.IntegerField(help_text='Игра для действий')
