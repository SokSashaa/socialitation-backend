import zipfile

from django.core.validators import FileExtensionValidator
from rest_framework import serializers

from socialize_main.models import Games

class BaseGameSerializer(serializers.Serializer):
    name = serializers.CharField(help_text='Название игры')
    description = serializers.CharField(help_text='Описание игры')
    icon = serializers.CharField(help_text='Иконка игры', required=False, allow_blank=True, allow_null=True)

class GameSerializer(serializers.ModelSerializer):

    class Meta:
        model = Games
        fields = ('id','name', 'description', 'link', 'icon')
        read_only_fields = ['id']


class CreateGameSerializer(BaseGameSerializer):
    archive_file = serializers.FileField(help_text='Архив игры',
                                         validators=[FileExtensionValidator(['zip'])])

    def validate_archive_file(self, archive):
        archive.seek(0)
        try:
            if archive.size > 10 * 1024 * 1024:
                raise serializers.ValidationError('ZIP файл больше 10 МБ')

            with zipfile.ZipFile(archive, 'r') as zip_ref:
                if 'index.html' not in zip_ref.namelist():
                    raise serializers.ValidationError('Отсутствует index.html файл')

        except zipfile.BadZipFile:
            return serializers.ValidationError('Архив поврежден или некорректен')

        archive.seek(0)
        return archive


class UpdateGameSerializer(BaseGameSerializer):
    pass

class SingleGameSerializer(serializers.Serializer):
    game = GameSerializer()

class GetUserGamesSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(help_text='ID юзера')
    name = serializers.CharField(required=False, allow_null=True, allow_blank=True,help_text='Название для поиска')

class AppointGameSerializer(serializers.Serializer):
    link = serializers.ListField(help_text='Список юзеров для привязки', child=serializers.IntegerField())
    unlink = serializers.ListField(help_text='Список юзеров для отвязки', child=serializers.IntegerField())
    game_id = serializers.IntegerField(help_text='Игра для действий')
