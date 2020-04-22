from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.postgres.fields import JSONField

from tinymce.models import HTMLField


PUBLIC = 'PUBLIC'
PRIVATE = 'PRIVATE'
PRIVACY_CHOICES = [
    (PUBLIC, 'Public'),
    (PRIVATE, 'Private'),
]

EDITION = 'EDITION'
TRANSLATION = 'TRANSLATION'
CONTENT_TYPE_CHOICES = [
    (EDITION, 'Edition'),
    (TRANSLATION, 'Translation'),
]


class CustomUser(AbstractUser):
    full_name = models.CharField(max_length=256, blank=True)
    bio = models.TextField(blank=True)
    tagline = models.TextField(blank=True)
    picture = models.ImageField(
        upload_to='images', blank=True)

    def __str__(self):
        return self.username

class Topic(models.Model):
    name = models.CharField(max_length=256)
    comments = models.ManyToManyField(
        'Lesson', related_name='topics_lessons', blank=True)

    def __str__(self):
        return self.name

class Lesson(models.Model):
    title = models.CharField(max_length=256, blank=True)
    topics = models.ManyToManyField('Topic', related_name='lessons_topics', blank=True)
    picture = models.ImageField(
        upload_to='images', blank=True)
    content = HTMLField(blank=True)

    def __str__(self):
        return self.username

class Collection(models.Model):
    title = models.CharField(max_length=256, blank=True)
    topics = models.ManyToManyField('Topic', related_name='collections_topics', blank=True)

    # possibly consider json field for this in the future
    items = models.TextField(blank=True)

    def __str__(self):
        return self.username
