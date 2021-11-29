from django.contrib.auth.models import AbstractUser
from django.contrib.postgres import fields
from django.db import models
from django.utils.text import slugify
import uuid

from tinymce.models import HTMLField


PUBLIC = 'PUBLIC'
PRIVATE = 'PRIVATE'
PRIVACY_CHOICES = [
    (PUBLIC, 'Public'),
    (PRIVATE, 'Private'),
]

class CustomUser(AbstractUser):
    full_name = models.CharField(max_length=256, blank=True)
    bio = models.TextField(blank=True)
    tagline = models.TextField(blank=True)
    picture = models.ImageField(upload_to='images', blank=True)
    
    def __str__(self):
        return self.username
    
    def save_search(self):
        """ This method will save a search to a user's profile """

    def get_saved_searches(self):
        """ This method will retrieve all saved searches associated to a user's profile """

class Search(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.TextField(blank=False)
    search = fields.JSONField(blank=False)
    name = models.TextField(blank=False)

    def __str__(self):
        return str(self.id)

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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=256)
    slug = models.SlugField(blank=True)
    public = models.BooleanField(blank=True, default=False)
    owners = models.ManyToManyField('CustomUser', related_name='owners', blank=True)
    topics = models.ManyToManyField('Topic', related_name='collections_topics', blank=True)
    contents = models.ManyToManyField('ElasticSearchItem', related_name='elasticsearchitem', blank=True)
    picture = models.ImageField(upload_to='images', blank=True)
    # contents = fields.JSONField(blank=False)

    def __str__(self):
        return str(self.id)

    def _get_unique_slug(self):
        unique_slug = slugify(self.title)
        num = 1
        for record in Collection.objects.filter(slug=unique_slug):
            unique_slug = '{}-{}'.format(slugify(self.title), num)
            num += 1
        return unique_slug

    def get(self):
        return self.contents

    def add(self, object):
        print(object, self.contents)

    def save(self, *args, **kwargs):
        self.slug = self._get_unique_slug()
        super().save(*args, **kwargs)

class ElasticSearchItem(models.Model):
    collection = models.ForeignKey(Collection, related_name='items', on_delete=models.CASCADE)
    type = models.CharField(max_length=20)
    es_id = models.IntegerField()

    def __str__(self):
        return "{}-{}".format(self.es_id, self.type)
