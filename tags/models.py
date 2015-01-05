import datetime
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import permalink, Count
from django.db.models.query import QuerySet
from django.db.transaction import atomic
from django.utils.timezone import now
from django.db import models
from django.template.defaultfilters import slugify


class Tag(models.Model):
    PRIMARY_TYPES = [
        ('technology', 'technology'),
        ('field', 'field'),
    ]
    ALLOWED_TYPES = PRIMARY_TYPES + [
        ('status', 'status'),
        ('category', 'category')
    ]
    WIP_TAG = 'wip'  # The special role for this tag makes it useful to set it as a field

    title = models.SlugField(max_length=50, unique=True)
    verbose_title = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    updated = models.DateTimeField(auto_now_add=True)
    tag_type = models.CharField(max_length=32, choices=ALLOWED_TYPES)

    @atomic
    def save(self, *args, **kwargs):
        self.title = slugify(self.title)
        titles = list(
            Tag.objects.exclude(pk=self.pk).filter(
                title__regex='^{}(-\d+)?$'.format(self.title)).values_list('title', flat=True))
        if titles:
            # There is at least one slug like the one we're trying to save, so we'll get the first available slot
            # First, we convert all the slug indexes to integers
            indexes = [0]+[int(x.replace(self.title+'-', '')) for x in titles if x != self.title]
            # Then we see what is the first int that has never been used - defaulting to the first one after max.
            # Since we have added an integer that has never been used, by definition, we are guaranteed at least one
            # useable digit.
            available = sorted(set(range(0, max(indexes)+2)) - set(indexes))[0]
            self.title = '{}-{}'.format(self.title, available)
        super(Tag, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('articles_list_by_tag', kwargs={'tag': self.title})

    def __unicode__(self):
        return self.verbose_title or self.title


class TaggableManager(models.Manager):
    def get_tags_by_count(self, tagged_objects=None):
        """
        Return a queryset of Tag objects annotated with their uses count (ie. how many times they appear in the given
        queryset - or the default queryset for this manager)

        :return: :rtype:
        """
        # The following is a bit cryptic, perhaps: what it does is simply find the name used to access this model
        # from Tag objects
        lookup = self.model.tags.field.related.get_accessor_name()
        qs = tagged_objects or self.get_queryset()
        if not isinstance(qs, QuerySet):
            # We have received a list or set of Taggable pks, so we have to get the Tag ids from that
            qs = self.get_queryset().filter(pk__in=tagged_objects)
        tag_ids = qs.values_list('tags', flat=True)
        return Tag.objects.filter(pk__in=tag_ids).annotate(uses_count=Count(lookup)).order_by('-uses_count')


class Taggable(models.Model):
    """
    Mixin to add tag-related functionality to objects
    """
    tags = models.ManyToManyField(Tag, related_name='tagged_%(class)s_set', blank=True, null=True)
    objects_as_tagged = TaggableManager()

    @transaction.atomic
    def set_tag(self, tag):
        created = False
        if not isinstance(tag, Tag):
            # in this case, we don't need to update the timestamp on the tag
            tag, created = Tag.objects.get_or_create(title=slugify(tag))
        if not created:
            tag.updated = now()
            tag.save()
        self.tags.add(tag)

    def has_tag(self, tag_title):
        return self.tags.filter(title=slugify(tag_title)).exists()

    @permalink
    def get_tag_list_url(self):
        return 'tags_tags_for_object', None, {'content_type': ContentType.objects.get_for_model(self).pk,
                                              'object_id': self.pk}

    class Meta:
        abstract = True