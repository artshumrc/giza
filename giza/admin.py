from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser, Lesson, Topic, Collection

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ['email', 'username', 'full_name']
    fieldsets = UserAdmin.fieldsets + (
            (None, {'fields': ('full_name', 'bio', 'tagline', 'picture')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Lesson)
admin.site.register(Topic)
admin.site.register(Collection)
