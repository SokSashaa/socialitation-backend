# Указывает Docker использовать официальный образ python 3 с dockerhub в качестве базового образа
FROM python:3
# Устанавливает переменную окружения, которая гарантирует, что вывод из python будет отправлен прямо в терминал без предварительной буферизации
ENV PYTHONUNBUFFERED 1
# Устанавливает рабочий каталог контейнера — "app"
WORKDIR /SocializationProject
# Копирует все файлы из нашего локального проекта в контейнер
ADD . /SocializationProject
COPY ../SocializationProject /SocializationProject/
COPY ./manage.py .
#ADD djangoProject .
# Запускает команду pip install для всех библиотек, перечисленных в requirements.txt
RUN pip install -r requirements.txt
CMD [ "python", "./manage.py", "runserver", "0.0.0.0:8000", "--settings=SocializationProject.settings.prod" ]
#CMD python manage.py runserver 127.0.0.1:8000