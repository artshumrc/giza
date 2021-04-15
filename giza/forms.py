from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from tinymce.widgets import TinyMCE
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV3

from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    captcha = ReCaptchaField(widget=ReCaptchaV3)
    class Meta:
        model = CustomUser
        fields = ('full_name', 'username', 'email',)

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('full_name', 'username', 'email',)
