import base64
import os

from django.core.files.base import ContentFile
from django.http import JsonResponse
from rest_framework import status

from SocializationProject import settings
from socialize_main.utils.random_number import random_number


def saving_image(serializer, field):
    try:
        if serializer.validated_data.get(field, False):
            image_data = serializer.validated_data[field]
            image_name = f"{random_number()}_photo.png"
            image_path = os.path.join(settings.MEDIA_ROOT, 'uploaded_images', image_name)

            os.makedirs(os.path.dirname(image_path), exist_ok=True)

            # Декодируем изображение из base64
            try:
                format, imgstr = image_data.split(';base64,')
            except ValueError:
                return JsonResponse({'success': False, 'errors': ['Неправильный формат изображения']},
                                    status=status.HTTP_400_BAD_REQUEST)

            data = ContentFile(base64.b64decode(imgstr), name=image_name)

            # Сохраняем изображение
            with open(image_path, 'wb') as destination:
                destination.write(data.read())

            # Формируем URL для сохраненного изображения
            image_url = os.path.join(settings.MEDIA_URL, 'uploaded_images', image_name)

            return image_url
        else:
            return ''
    except KeyError as e:
            return JsonResponse({
                'success': False,
                'error': f'Не найдено обязательное поле: {e}'
            }, status=status.HTTP_400_BAD_REQUEST)
