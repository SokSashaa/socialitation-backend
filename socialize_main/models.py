from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models


# Create your models here.


class Organization(models.Model):
    name = models.CharField(blank=False, null=False, max_length=150)
    address = models.CharField(blank=False, null=False, max_length=150)
    phone_numer = models.CharField(blank=False, null=False, max_length=150)
    email = models.CharField(blank=False, null=False, max_length=150)
    site = models.CharField(blank=True, null=True, max_length=150)


class User(models.Model):
    login = models.CharField(blank=False, null=False, unique=True, max_length=150)
    email = models.CharField(blank=False, null=False, unique=True, max_length=150)
    second_name = models.CharField(blank=True, null=True, max_length=150)
    name = models.CharField(blank=True, null=True, max_length=150)
    last_name = models.CharField(blank=True, null=True, max_length=150)




class Researcher(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='researcher_user')
    organization = models.ForeignKey(Organization, on_delete=models.DO_NOTHING, related_name='researcher_organization')


class Tutor(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='tutor_user')
    organization = models.ForeignKey(Organization, on_delete=models.DO_NOTHING, related_name='tutor_organization')


class Observed(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='observed_user')
    tutor = models.ForeignKey(Tutor, on_delete=models.DO_NOTHING, related_name='observed_tutor')
    organization = models.ForeignKey(Organization, on_delete=models.DO_NOTHING, related_name='observed_organization')
    date_of_birth = models.DateField(blank=False, null=False)
    address = models.CharField(blank=False, null=False, max_length=150)
    phone_number = models.CharField(blank=False, null=False, max_length=150)


class Administrator(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='administrator_user')


class Tests(models.Model):
    title = models.CharField(blank=False, null=False, max_length=150)
    description = models.CharField(blank=False, null=False, max_length=150)


class TestObservered(models.Model):
    test = models.ForeignKey(Tests, on_delete=models.DO_NOTHING)
    observed = models.ForeignKey(Observed, on_delete=models.DO_NOTHING)


class PointRange(models.Model):
    test = models.ForeignKey(Tests, on_delete=models.DO_NOTHING, related_name='point_range_test')
    result = models.IntegerField()
    high_border = models.IntegerField(blank=False, null=False)
    low_border = models.IntegerField(blank=False, null=False)


class TestQuestions(models.Model):
    test = models.ForeignKey(Tests, on_delete=models.DO_NOTHING, related_name='test_question_test')
    question = models.CharField(blank=False, null=False, max_length=150)


class TestResult(models.Model):
    test = models.ForeignKey(Tests, on_delete=models.DO_NOTHING, related_name='test_result_test')
    observed = models.ForeignKey(Observed, on_delete=models.DO_NOTHING, related_name='test_result_observed')


class Answers(models.Model):
    question = models.ForeignKey(TestQuestions, on_delete=models.DO_NOTHING, related_name='answer_question')
    description = models.CharField(blank=False, null=False, max_length=150)
    point = models.IntegerField(blank=False, null=False)


class ObservedAnswer(models.Model):
    test_result = models.ForeignKey(TestResult, on_delete=models.DO_NOTHING)
    observed = models.ForeignKey(Observed, on_delete=models.DO_NOTHING)


class Games(models.Model):
    name = models.CharField(blank=False, null=False, max_length=150)
    description = models.CharField(blank=False, null=False, max_length=150)
    link = models.CharField(blank=False, null=False, max_length=150)


class GamesObserved(models.Model):
    observed = models.ForeignKey(Observed, on_delete=models.DO_NOTHING)
    game = models.ForeignKey(Games, on_delete=models.DO_NOTHING)
