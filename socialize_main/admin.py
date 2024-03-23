from django.contrib import admin
from .models import *
# Register your models here.


admin.site.register(Organization)
admin.site.register(User)
admin.site.register(Researcher)
admin.site.register(Tutor)
admin.site.register(Observed)
admin.site.register(Administrator)
admin.site.register(TestObservered)
admin.site.register(PointRange)
admin.site.register(TestQuestions)
admin.site.register(TestResult)
admin.site.register(Answers)
admin.site.register(ObservedAnswer)
admin.site.register(Games)
admin.site.register(GamesObserved)