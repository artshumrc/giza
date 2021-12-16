from django.contrib.auth.models import AbstractUser
from django.contrib.postgres import fields
from django.db import models
from django.utils.text import slugify
from django.core.files import File
import uuid, os
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import ugettext_lazy as _

from tinymce.models import HTMLField

# PUBLIC = 'PUBLIC'
# PRIVATE = 'PRIVATE'
# PRIVACY_CHOICES = [
#     (PUBLIC, 'Public'),
#     (PRIVATE, 'Private'),
# ]

def get_upload_path(instance, filename):
    return os.path.join('images', 'collections', instance.id, filename)




class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """
    def create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    username = models.CharField(max_length=256, blank=True)
    email = models.EmailField(_('email address'), unique=True)
    full_name = models.CharField(max_length=256, blank=True)
    bio = models.TextField(blank=True)
    tagline = models.TextField(blank=True)
    picture = models.ImageField(upload_to='images', blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()
    
    def __str__(self):
        return self.email
    
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    slug = models.SlugField(blank=True)
    picture = models.ImageField(upload_to='images', blank=True)

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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=256, blank=True)
    slug = models.SlugField(blank=True)
    topics = models.ManyToManyField('Topic', related_name='lessons_topics', blank=True)
    collections = models.ManyToManyField('Collection', related_name='collections_topics', blank=True)
    picture = models.ImageField(upload_to='images', blank=True)
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
    topics = models.ManyToManyField('Topic', related_name='topics', blank=True)
    contents = models.ManyToManyField('ElasticSearchItem', related_name='contents', blank=True)
    picture = models.ImageField(upload_to=get_upload_path, blank=True)

    def __str__(self):
        return str(self.id)

    # def _get_unique_slug(self):
    #     unique_slug = slugify(self.title)
    #     num = 1
    #     for record in Collection.objects.filter(slug=unique_slug):
    #         unique_slug = '{}-{}'.format(slugify(self.title), num)
    #         num += 1
    #     return unique_slug

    def get(self):
        return self.contents

    def add(self, object):
        print(object, self.contents)

    def save(self, *args, **kwargs):

        # f = open(os.path.join(os. getcwd(), 'static', 'img', 'thumb-default.png'), 'w')
        # make folder
        # store image path default
        self.picture = 'thumb-default.png'
        # self.slug = self._get_unique_slug()
        super().save(*args, **kwargs)

class ElasticSearchItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    collection = models.ForeignKey(Collection, related_name='items', on_delete=models.CASCADE)
    type = models.CharField(max_length=20)
    es_id = models.IntegerField()

    def __str__(self):
        return "{}-{}".format(self.es_id, self.type)