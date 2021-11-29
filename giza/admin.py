from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser, Lesson, Topic, Collection, ElasticSearchItem

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ['email', 'username', 'full_name']
    fieldsets = UserAdmin.fieldsets + (
            (None, {'fields': ('full_name', 'bio', 'tagline', 'picture')}),
    )


class ElasticsearchItemInline(admin.TabularInline):
    model = ElasticSearchItem

class CollectionAdmin(admin.ModelAdmin):
    readonly_fields=('slug',)

    inlines = [
        ElasticsearchItemInline,
    ]

class LessonAdmin(admin.ModelAdmin):
    readonly_fields=('slug',)

class TopicAdmin(admin.ModelAdmin):
    readonly_fields=('slug',)

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Lesson, LessonAdmin)
admin.site.register(Topic, TopicAdmin)
admin.site.register(Collection, CollectionAdmin)
