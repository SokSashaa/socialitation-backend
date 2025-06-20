import datetime

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin, AbstractUser
from django.db import models

from socialize_main.managers import CustomUserManager


# Create your models here.


class Organization(models.Model):
    name = models.CharField(blank=False, null=False, max_length=150)
    address = models.CharField(blank=False, null=False, max_length=150)
    phone_number = models.CharField(blank=False, null=False, max_length=150, unique=True)
    email = models.CharField(blank=False, null=False, max_length=150, unique=True)
    site = models.CharField(blank=True, null=True, max_length=150)


class User(AbstractUser):
    email = models.CharField(blank=True, null=True, unique=True, max_length=150)
    username = None
    second_name = models.CharField(blank=False, null=False, max_length=150)
    name = models.CharField(blank=False, null=False, max_length=150)
    login = models.CharField(blank=False, null=False, unique=True, max_length=100)
    photo = models.CharField(blank=True, null=True, max_length=500)
    phone_number = models.CharField(blank=False, null=False, max_length=12, unique=True)
    patronymic = models.CharField(blank=True, null=True, max_length=150)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='organization')
    birthday = models.DateField(blank=False, null=False, default='1990-01-01')
    REQUIRED_FIELDS = []
    USERNAME_FIELD = 'login'
    objects = CustomUserManager()

    def __str__(self):
        return self.login


class Tutor(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tutor_user')


class Observed(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='observed_user')
    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='observed_tutor')
    address = models.CharField(blank=False, null=False, max_length=150)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(~models.Q(user=models.F('tutor'))),
                name="user_and_tutor_cannot_be_the_same"
            )
        ]


class Administrator(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='administrator_user')


class Tests(models.Model):
    title = models.CharField(blank=False, null=False, max_length=150)
    description = models.CharField(blank=True, null=True, max_length=300)
    created_at = models.DateTimeField('Создан', default=datetime.datetime.now)


class TestObservered(models.Model):
    test = models.ForeignKey(Tests, on_delete=models.CASCADE)
    observed = models.ForeignKey(Observed, on_delete=models.CASCADE)
    is_passed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['test', 'observed'],
                name='primary_unique_test_observed'
            )
        ]


class TestQuestions(models.Model):
    test = models.ForeignKey(Tests, on_delete=models.CASCADE, related_name='test_question_test')
    title = models.CharField(blank=False, null=False, max_length=150)
    type = models.CharField(blank=False, null=False, max_length=150, default='checkbox')
    required = models.BooleanField(default=True)


class TestResult(models.Model):
    test = models.ForeignKey(Tests, on_delete=models.CASCADE, related_name='test_result_test')
    observed = models.ForeignKey(Observed, on_delete=models.CASCADE, related_name='test_result_observed')


class Answers(models.Model):
    question = models.ForeignKey(TestQuestions, on_delete=models.CASCADE, related_name='answer_question')
    text = models.CharField(blank=False, null=False, max_length=150)
    point = models.IntegerField(blank=False, null=False)


class ObservedAnswer(models.Model):
    test_result = models.ForeignKey(TestResult, on_delete=models.CASCADE, related_name='answers')
    answer = models.ForeignKey(Answers, on_delete=models.CASCADE, blank=True, null=True)


class Games(models.Model):
    name = models.CharField(blank=False, null=False, max_length=150)
    description = models.CharField(blank=False, null=False, max_length=300)
    link = models.CharField(blank=False, null=False, max_length=500)
    directory_name = models.CharField(blank=False, null=False, max_length=150, unique=True, editable=False)
    icon = models.CharField(blank=True, null=True, max_length=500)


class GamesObserved(models.Model):
    observed = models.ForeignKey(Observed, on_delete=models.CASCADE)
    game = models.ForeignKey(Games, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['game', 'observed'],
                name='primary_unique_games_observed'
            )
        ]
