# coding=utf-8
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.db import models, IntegrityError
from django.db.models import permalink, F, Q
from django.db.transaction import atomic
from django.forms import model_to_dict
from django.template.defaultfilters import striptags, slugify
from django.utils.timezone import now
from datetime import timedelta
from markdown import markdown
import re
from profiles.models import Author
from scoring.models import ScoreTransaction
from tags.models import Taggable, Tag


class ArticleManager(models.Manager):
    def sorted_by_hot(self, qs=None, from_date=None):
        # This is the decay function:
        # http://www.wolframalpha.com/input/?i=exp%28-0.05*x*x%29
        # I tried to keep a soft decay for the first week

        tz_now = now()
        if qs is None:
            qs = self.get_queryset()
        if not from_date:
            from_date = tz_now - timedelta(days=7)

        # qs = qs.filter(kudos_received__timestamp__gt=from_date)
        # qs = qs.annotate(points=Count('kudos_received'))
        # for article in qs:
        #     daysago = (tz_now - article.published_at).total_seconds() / 86400
        #     s = math.log(max(article.points, 1)) * math.exp(-0.05 * daysago * daysago)
        #     article.hotness = s
        # qs = sorted(qs, key=lambda r: r.hotness, reverse=True)
        # return qs
        # The following is a postgresql-compliant implementation of the above; it should be safely switchable
        qs = qs.exclude(published_at__isnull=True).extra(select={
            'hotness': "select LOG((points+1) * EXP(-0.05 * days_ago * days_ago)) "
                       "from "
                       "(select LEAST(7, DATE_PART('day', DATE %s - published_at)) as days_ago) ttt, "
                       "(select COUNT(*) as points from articles_kudos where "
                       "article_id=articles_article.id AND timestamp>%s) ttt2",
        }, select_params=[tz_now.strftime('%Y-%m-%d'), from_date.strftime('%Y-%m-%d')])
        return qs.distinct().order_by('-hotness')

    def get_trending_tags(self):
        tz_now = now()
        from_date = tz_now - timedelta(days=31)

        items = self.sorted_by_hot(from_date=from_date)  # There's a minor difficulty here: we can't easily filter out non-hot articles
        # unless we use the queryset variant, so a list comprehension is required
        return Article.objects_as_tagged.get_tags_by_count([a.pk for a in items if a.hotness > 0])

    def get_wip_articles(self):
        return self.get_queryset().filter(tags__title=Tag.WIP_TAG)

    def get_queryset_for_user(self, user=None):
        qs = self.get_queryset().prefetch_related('tags').prefetch_related('articlegroup_set')
        #if user.is_superuser:
        #    return qs
        # Normally visible articles have to be published and not deleted
        filters = Q(published_at__isnull=False)
        if user and user.is_authenticated():  # Authors can see both unpublished and deleted articles
            filters = filters | Q(author=user)
        return qs.filter(filters)

    def get_editable_for_user(self, user=None):
        qs = self.get_queryset()
        #if user.is_superuser:
        #    return qs
        # Normally visible articles have to be published and not deleted
        filters = Q(is_wiki=True)
        if user.is_authenticated():  # Authors can see both unpublished and deleted articles
            filters = filters | Q(author=user)
        return qs.filter(filters)


class NonDeletedArticleManager(ArticleManager):
    def get_queryset(self):
        return super(NonDeletedArticleManager, self).get_queryset().filter(deleted_at__isnull=True).select_related(
            'author', 'original_author', 'author__author_profile',
            'original_author__author_profile')


class Article(Taggable, models.Model):
    # The user who authored the current revision
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    # The user who authored the first version of the Article
    original_author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_articles', blank=True,
                                        null=True)

    slug = models.SlugField(max_length=255)
    title = models.CharField(max_length=255)
    description = models.TextField()
    punchline = models.CharField(max_length=255)
    rendered_html = models.TextField(blank=True)
    raw_content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    published_at = models.DateTimeField(blank=True, null=True)
    is_wiki = models.BooleanField(default=False)
    hide = models.BooleanField(default=False)

    submitted_at = models.DateTimeField(editable=False, blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    views_count = models.PositiveIntegerField(default=0)
    received_kudos_count = models.PositiveIntegerField(default=0)
    editors_count = models.PositiveIntegerField(default=1)
    revisions_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    links_count = models.PositiveIntegerField(default=0)

    keywords = models.TextField(blank=True, null=True)

    all_objects = ArticleManager()  # Full version with all articles, positioned as default manager (for the admin)
    objects = NonDeletedArticleManager()  # This one does not show the articles with deleted_at != None
    # frontpage = FrontpageManager()

    def __unicode__(self):
        return self.title

    def update_from_raw_content(self):
        data = Article.process_raw_content(self.raw_content)
        data.pop('raw_content', None)
        for key, value in data.items():
            if value:  # At the moment, I can't see a reason to blanking out values
                setattr(self, key, value)

    @atomic
    def save(self, *args, **kwargs):
        existing = False
        self.update_from_raw_content()
        revision_data = model_to_dict(self, ['title', 'description', 'punchline', 'raw_content', 'rendered_html'])
        if self.pk:  # We're updating an instance, so we should check for "fake" revisions
            existing = self.revision_set.filter(**revision_data).exists()
            if not existing:
                self.revisions_count += 1
            other_editors = self.revision_set.exclude(author=self.author).values_list('author_id').distinct().count()
            self.editors_count = other_editors + 1  # Current editor
            # If the instance has a PK, we'll also ensure wiki+WIP consistency
            if not self.is_wiki:
                self.is_wip = False
        else:  # Since it's the first time we're saving this, we're also going to fill in the value for original_author
            self.original_author = self.author
        self.slug = slugify(self.title)
        self.links_count = self.count_own_links()
        super(Article, self).save(*args, **kwargs)
        published_count = self.original_author.created_articles.filter(published_at__isnull=False).count()
        self.original_author.author_profile.articles_published_count = published_count
        self.original_author.author_profile.save()
        if not existing:
            revision_data['author'] = self.author  # Needed to avoid complaints about the FK not being an instance
            self.revision_set.create(**revision_data)
            self.author.author_profile.edits_count += 1
            self.author.author_profile.save()

    @property
    def other_contributors(self):
        return self.all_contributors().exclude(pk=self.original_author.pk)

    @property
    def all_contributors(self):
        """
        Return all users who contributed an edit to the article, sorted by oldest revision first.

        :return: :rtype: User queryset
        """
        return get_user_model().objects.select_related('author_profile')\
            .filter(pk__in=self.revision_set.values_list('author', flat=True))\
            .order_by('revision__pk')

    def award_points_to_author(self):
        self.original_author.scoretransaction_set.create(change=settings.ACTIVITY_POINTS['receiving_kudos_as_author'],
                                                         operation='Received kudos for article {}'.format(self.pk))

    def award_points_to_editors(self):
        editors = self.revision_set.exclude(author=self.original_author).values_list('author', flat=True)
        score_change = settings.ACTIVITY_POINTS['receiving_kudos_as_editor']
        # We want to create this in a bulk operation, so the ScoreTransaction.save() method wouldn't get called
        # This means that we need to manually update the editors' scores.
        Author.objects.filter(user__in=editors).update(score=F('score') + score_change)
        editor_scores = [ScoreTransaction(user_id=editor,
                                          change=settings.ACTIVITY_POINTS['receiving_kudos_as_editor'],
                                          operation='Received kudos for editing article {}'.format(self.pk))
                         for editor in editors]
        ScoreTransaction.objects.bulk_create(editor_scores)

    @atomic
    def receive_kudos(self, session_id='', user=None):
        try:
            kudos = Kudos.objects.create(article=self, session_id=session_id, user=user)
        except IntegrityError:
            pass
        else:
            self.kudos_received.add(kudos)
            self.received_kudos_count += 1
            self.save()
            self.award_points_to_author()
            self.award_points_to_editors()
            if user is not None and user.is_authenticated():
                user.author_profile.kudos_given_count += 1
                user.author_profile.save()
        return self.received_kudos_count

    @atomic
    def receive_view(self, session_id='', user=None):
        ArticleView.objects.create(article=self, session_id=session_id, user=user)
        # To avoid all the mess with saving revisions etc.
        Article.objects.filter(pk=self.pk).update(views_count=F('views_count')+1)

    @permalink
    def get_absolute_url(self):
        return 'articles_article_detail', (self.pk, ),

    def get_canonical_url(self):
        return reverse('articles_article_detail', args=(self.pk, self.slug))

    def get_edit_url(self):
        if self.pk:
            return reverse('articles_article_edit', args=(self.pk, ))

    def get_save_url(self):
        if self.pk:
            return reverse('articles_article_rest_save', args=(self.pk, ))

    def get_delete_url(self):
        if self.pk:
            return reverse('articles_article_rest_delete', args=(self.pk, ))

    def get_publish_url(self):
        if self.pk:
            return reverse('articles_article_rest_publish', args=(self.pk, ))

    @permalink
    def get_source_url(self):
        return 'articles_article_source', (self.pk, ),

    @property
    def is_wip(self):
        # Since we *should* normally have prefetch_related, we should leverage it here:
        if 'tags' in getattr(self, '_prefetched_objects_cache', []):
            return Tag.WIP_TAG in [t.title for t in self.tags.all()]
        return self.has_tag(Tag.WIP_TAG)

    @is_wip.setter
    def is_wip(self, value):
        wip, created = Tag.objects.get_or_create(title=Tag.WIP_TAG, defaults={'tag_type': 'status'})
        if value:
            self.is_wiki = True
            self.save()
            self.set_tag(wip)
        elif self.pk:  # If the article has no PK, it cannot have been marked as WIP.
            self.tags.remove(wip)

    @property
    def primary_tag(self):
        try:
            return self.tags.filter(tag_type__in=[t[0] for t in Tag.PRIMARY_TYPES])[0]
        except IndexError:
            return None

    def is_editable_by_user(self, user=None):
        if user is not None and (user == self.author or user.is_superuser):
            return True
        if self.is_wiki:
            return True
        return False

    def is_editors_pick(self):
        # FIXME: Probably this should be denormalized, somewhere down the road
        return self.articlegroup_set.exists()

    @property
    def is_published(self):
        return self.published_at is not None

    @staticmethod
    def count_links(text):
        # full_re = r'(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](
        # ?:com|net|org|edu|gov|mil|aero|asia|biz|cat' \
        #           r'|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq
        # |ar' \
        #           r'|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch' \
        #           r'|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk' \
        #           r'|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il' \
        #           r'|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu
        # |lv' \
        #           r'|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no
        # |np' \
        #           r'|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh
        # |si' \
        #           r'|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw
        # |tz' \
        #           r'|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)' \
        #           r'(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)' \
        #           r'[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*' \
        #           r'[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro
        # |tel|' \
        #           r'travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm' \
        #           r'|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj' \
        #           r'|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq' \
        #           r'|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km
        # |kn' \
        #           r'|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms
        # |mt' \
        #           r'|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt
        # |pw' \
        #           r'|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc
        # |td' \
        #           r'|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye
        # |yt' \
        #           r'|yu|za|zm|zw)\b/?(?!@)))'
        # The above is taken from here: https://gist.github.com/gruber/8891611 and it might be useful if we need
        # to be more strict with URL checking; for the time being, I think that checking for http(s) should be enough.
        basic_re = r'(?:ht|f)tps?://\S+'
        return len(set(re.findall(basic_re, text)))

    def count_own_links(self):
        return self.count_links(self.raw_content)

    @staticmethod
    def process_raw_content(raw_content):
        """
        Processes a markdown-formatted string, returning a dict that can be used to populate an Article instance

        :param raw_content: markdown string
        :return: :rtype: dict
        """
        data = {}
        # Since we already have BeautifulSoup in the requirements, it makes sense to leverage it here.
        data['full_rendered_content'] = markdown(raw_content)
        soup = BeautifulSoup(data['full_rendered_content'])
        try:
            data['title'] = soup.find('h1').extract().encode_contents()
        except AttributeError:  # Element not found
            data['title'] = ''
        # Markdown seems to add a paragraph and extra linebreaks inside blockquotes for some reason; in pre_v1 any HTML
        # was skipped, but it was decided to  so we'll do the same here, and we'll remove the linebreaks too.
        try:
            data['punchline'] = soup.find('blockquote').extract().find('p').encode_contents().strip()
        except AttributeError:
            data['punchline'] = ''
        try:
            # Slightly more complex: we need to find the first H2, and extract the first P before it
            data['description'] = soup.find('h2').find_previous('p').extract().encode_contents()
        except AttributeError:
            data['description'] = ''
        data['rendered_html'] = soup.encode_contents()
        return data


class Kudos(models.Model):
    article = models.ForeignKey(Article, related_name='kudos_received')
    session_id = models.CharField(max_length=32)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='kudos_given')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [
            ('article', 'session_id'),
            ('article', 'user'),
        ]


class ArticleView(models.Model):
    article = models.ForeignKey(Article)
    session_id = models.CharField(max_length=32)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='viewed_pages')
    timestamp = models.DateTimeField(auto_now_add=True)


class ArticleGroupManager(models.Manager):
    def get_current_for_block(self, block_name):
        return self.get_queryset().filter(publish_start__isnull=False, target_block=block_name).latest()

    def get_editors_picks(self, user=None):
        try:
            return self.get_current_for_block('editors_picks').articles.get_queryset_for_user(user)
        except ArticleGroup.DoesNotExist:
            return Article.objects.none()

    def get_promoted_wip(self, user=None):
        try:
            return self.get_current_for_block('wip').articles.get_queryset_for_user(user)
        except ArticleGroup.DoesNotExist:
            return Article.objects.none()


class ArticleGroup(models.Model):
    articles = models.ManyToManyField(Article, blank=True, null=True)
    publish_start = models.DateTimeField(blank=True, null=True)
    target_block = models.CharField(max_length=255, default="editors_picks")

    objects = ArticleGroupManager()

    def __unicode__(self):
        return self.publish_start.strftime("%d/%m/%Y %H:%M:%S")

    class Meta:
        get_latest_by = 'publish_start'


class Revision(models.Model):
    article = models.ForeignKey(Article)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    created_at = models.DateTimeField(auto_now_add=True)

    title = models.CharField(max_length=255)
    description = models.TextField()
    punchline = models.CharField(max_length=255)
    raw_content = models.TextField()
    rendered_html = models.TextField(blank=True)

    def __unicode__(self):
        return self.title

    class Meta:
        get_latest_by = 'pk'
        ordering = ['-pk']
