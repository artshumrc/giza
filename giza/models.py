# from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import AbstractUser
# from django.contrib.postgres import fields
from django.db.models import JSONField, EmailField, CharField, TextField, ImageField, UUIDField, ManyToManyField, BooleanField, ForeignKey, IntegerField, Model, CASCADE
# from django.db import models
# from django.utils.text import slugify
# from django.core.files import File
import uuid, os
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _

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
    username = CharField(max_length=256, blank=True, unique=False)
    email = EmailField(_('email address'), unique=True)
    full_name = CharField(max_length=256, blank=True)
    first_name = CharField(max_length=256)
    last_name = CharField(max_length=256)
    bio = TextField(blank=True)
    tagline = TextField(blank=True)
    picture = ImageField(upload_to='images', blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()
    
    def __str__(self):
        return self.email
    
    def save_search(self):
        """ This method will save a search to a user's profile """

    def get_saved_searches(self):
        """ This method will retrieve all saved searches associated to a user's profile """

class Search(Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = TextField(blank=False)
    search = JSONField(blank=False)
    name = TextField(blank=False)

    def __str__(self):
        return str(self.id)

class Topic(Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = CharField(max_length=256)
    # slug = models.SlugField(blank=True)
    picture = ImageField(default='/images/default.png', upload_to='images', blank=True)

    def __str__(self):
        return self.name

    # def _get_unique_slug(self):
    #     unique_slug = slugify(self.name)
    #     num = 1
    #     for record in Topic.objects.filter(slug=unique_slug):
    #         unique_slug = '{}-{}'.format(slugify(self.title), num)
    #         num += 1
    #     return unique_slug

    def save(self, *args, **kwargs):
        # if not self.slug:
            # self.slug = self._get_unique_slug()
        super().save(*args, **kwargs)

class Lesson(Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = CharField(max_length=256, blank=True)
    # slug = models.SlugField(blank=True)
    topics = ManyToManyField('Topic', related_name='lessons_topics', blank=True)
    collections = ManyToManyField('Collection', related_name='collections_topics', blank=True)
    picture = ImageField(default='/images/default.png', upload_to='images', blank=True)
    summary = TextField(blank=True)
    content = HTMLField(blank=True)

    def __str__(self):
        return self.title

    # def _get_unique_slug(self):
    #     unique_slug = slugify(self.title)
    #     num = 1
    #     for record in Lesson.objects.filter(slug=unique_slug):
    #         unique_slug = '{}-{}'.format(slugify(self.title), num)
    #         num += 1
    #     return unique_slug

    def save(self, *args, **kwargs):
        # if not self.slug:
        #     self.slug = self._get_unique_slug()
        super().save(*args, **kwargs)

class Collection(Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = CharField(max_length=256)
    # slug = models.SlugField(blank=True)
    public = BooleanField(blank=True, default=False)
    owners = ManyToManyField('CustomUser', related_name='owners', blank=True)
    topics = ManyToManyField('Topic', related_name='topics', blank=True)
    contents = ManyToManyField('ElasticSearchItem', related_name='contents', blank=True)
    # picture = ImageField(upload_to=get_upload_path, blank=True)
    picture = ImageField(default='/images/default.png', upload_to='images', blank=True)

    def __str__(self):
        return str(self.title)

    # def _get_unique_slug(self):
    #     unique_slug = slugify(self.title)
    #     num = 1
    #     for record in Collection.objects.filter(slug=unique_slug):
    #         unique_slug = '{}-{}'.format(slugify(self.title), num)
    #         num += 1
    #     return unique_slug

    def get(self):
        return self.contents

    # def add(self, object):
    #     self.contents
    #     for record in Collection.objects.filter(id=self.id):
    #         print(record, object)
    #         # self.contents
            # id
            # collection_id
            # elasticsearchitem_id
            # print(object, self.contents)

    def save(self, *args, **kwargs):

        # f = open(os.path.join(os. getcwd(), 'static', 'img', 'thumb-default.png'), 'w')
        # make folder
        # store image path default
        self.picture = 'thumb-default.png'
        # self.slug = self._get_unique_slug()
        super().save(*args, **kwargs)

class ElasticSearchItem(Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    collection = ForeignKey(Collection, related_name='items', on_delete=CASCADE)
    type = CharField(max_length=20)
    es_id = IntegerField()

    def __str__(self):
        return "{}-{}".format(self.es_id, self.type)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return self