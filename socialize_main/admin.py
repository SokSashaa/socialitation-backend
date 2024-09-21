from django.contrib import admin

from django.contrib.auth.admin import UserAdmin
from .models import *

class CustomUserAdmin(UserAdmin):

    model = User
    list_display = ('login', 'is_staff', 'is_active',)
    list_filter = ('login', 'is_staff', 'is_active',)
    fieldsets = (
        (None, {'fields': ('login', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'is_active','groups')}),
        ('Профиль', {'fields': ('name', 'second_name', 'patronymic', 'photo')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'login', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('login',)
    ordering = ('login',)


admin.site.register(Organization)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Tests)
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
