from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import post_save
import markdown


class Author(models.Model):
    user = models.OneToOneField(User, related_name='author_profile')
    display_name = models.CharField(max_length=50)
    bio = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, default='')
    can_publish = models.BooleanField(default=False)
    score = models.PositiveIntegerField(default=1)  # Formerly known as karma
    articles_published_count = models.PositiveIntegerField(default=0)
    edits_count = models.PositiveIntegerField(default=0)
    kudos_given_count = models.PositiveIntegerField(default=0)

    def __unicode__(self):
        return self.display_name

    def get_absolute_url(self):
        return reverse('profiles_profile', kwargs={'username': self.username})

    @property
    def username(self):
        return self.user.username

    @property
    def email(self):
        return self.user.email

    @property
    def bio_html(self):
        return markdown.markdown(self.bio)

    @property
    def github_profile_url(self):
        return 'https://github.com/{}'.format(self.username)


def handler_profile_creator(sender, instance, created, *args, **kwargs):
    if created:
        Author.objects.create(user=instance, display_name=instance.username)


post_save.connect(handler_profile_creator, User, weak=False, dispatch_uid='profile_creator')
