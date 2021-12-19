from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordResetForm, PasswordChangeForm
from tinymce.widgets import TinyMCE

from .models import CustomUser, Collection

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('full_name', 'email',)

class CustomPasswordResetForm(PasswordResetForm):
    email = forms.CharField(required=True, label="Email address")
    class Meta:
        model = CustomUser
        fields = ('email',)

class CustomPasswordChangeForm(PasswordChangeForm):
    email = forms.CharField(required=True, label="Email address")
    class Meta:
        model = CustomUser
        fields = ('email', )

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('full_name', 'email',)

class CollectionForm(forms.ModelForm):
    title = forms.CharField(required=False, label="Name your new collection")
    class Meta:
        model = Collection
        fields = ('title', )
