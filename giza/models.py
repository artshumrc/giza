from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.utils.text import slugify

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
    slug = models.SlugField(blank=True)
    picture = models.ImageField(
        upload_to='images', blank=True)

    def __str__(self):
        return self.name

    def _get_unique_slug(self):
        unique_slug = slugify(self.name)
        num = 1
        for record in Topic.objects.filter(slug=unique_slug):
            unique_slug = '{}-{}'.format(slugify(self.title), num)
            num += 1
        return unique_slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._get_unique_slug()
        super().save(*args, **kwargs)

class Lesson(models.Model):
    title = models.CharField(max_length=256, blank=True)
    slug = models.SlugField(blank=True)
    topics = models.ManyToManyField('Topic', related_name='lessons_topics', blank=True)
    collections = models.ManyToManyField('Collection', related_name='collections_topics', blank=True)
    picture = models.ImageField(
        upload_to='images', blank=True)
    summary = models.TextField(blank=True)
    content = HTMLField(blank=True)

    def __str__(self):
        return self.title

    def _get_unique_slug(self):
        unique_slug = slugify(self.title)
        num = 1
        for record in Lesson.objects.filter(slug=unique_slug):
            unique_slug = '{}-{}'.format(slugify(self.title), num)
            num += 1
        return unique_slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._get_unique_slug()
        super().save(*args, **kwargs)

class Collection(models.Model):
    title = models.CharField(max_length=256)
    slug = models.SlugField(blank=True)
    owners = models.ManyToManyField(
        'CustomUser', related_name='owners', blank=True)
    topics = models.ManyToManyField('Topic', related_name='collections_topics', blank=True)
    picture = models.ImageField(
        upload_to='images', blank=True)

    # possibly consider json field for this in the future
    items = models.TextField(blank=True)

    def __str__(self):
        return self.title

    def _get_unique_slug(self):
        unique_slug = slugify(self.title)
        num = 1
        for record in Collection.objects.filter(slug=unique_slug):
            unique_slug = '{}-{}'.format(slugify(self.title), num)
            num += 1
        return unique_slug

    def save(self, *args, **kwargs):
        self.slug = self._get_unique_slug()
        super().save(*args, **kwargs)
