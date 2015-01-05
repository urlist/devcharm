from django.contrib.syndication.views import Feed
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.utils.feedgenerator import Rss201rev2Feed
from articles.models import Article
from tags.models import Tag


class DevCharmFeed(Rss201rev2Feed):
    def add_item_elements(self, handler, item):
        super(DevCharmFeed, self).add_item_elements(handler, item)
        handler.addQuickElement('authorLink', item['author_link'])
        handler.addQuickElement('author', item['author_name'])


class ArticleFeedByTag(Feed):
    request = None
    feed_type = DevCharmFeed

    def __call__(self, request, *args, **kwargs):
        self.request = request
        return super(ArticleFeedByTag, self).__call__(request, *args, **kwargs)

    def get_object(self, request, tag=None, *args, **kwargs):
        return get_object_or_404(Tag, title=tag)

    def items(self, obj):
        return Article.objects.filter(tags=obj, published_at__isnull=False)\
            .select_related('author', 'author__author').order_by('-published_at')

    def link(self, obj):
        if obj:
            return reverse('articles_feed_by_tag', args=(obj.title,))
        return reverse('articles_feed_global')

    def description(self, obj):
        return "New articles from Devcharm"

    def title(self, obj):
        # title = "What's new on Devcharm"  # Original attribute
        if obj:
            return u'Recent pages in {}'.format(obj.title)
        else:
            return u'Recent pages'

    def item_description(self, item):
        return item.punchline

    def item_pubdate(self, item):
        return item.published_at

    def item_author_name(self, item):
        return item.author.author_profile.display_name

    def item_author_link(self, item):
        return self.request.build_absolute_uri(item.author.author_profile.get_absolute_url())


class ArticleFeedGlobal(ArticleFeedByTag):
    def get_object(self, request, *args, **kwargs):
        return None


class RevisionFeed(ArticleFeedByTag):
    def get_object(self, request, pk=None, *args, **kwargs):
        return get_object_or_404(Article.objects.get_queryset_for_user(self.request.user), pk=pk)

    def items(self, obj):
        return obj.revision_set.select_related('author', 'author__author').order_by('-pk')

    def link(self, obj):
        return reverse('articles_article_revision_feed', kwargs={'pk': obj.pk, 'slug': obj.slug})

    def description(self, obj):
        return u'New revisions for "{}"'.format(obj.title)

    def item_link(self, item):
        return reverse('articles_article_revision_detail', kwargs={'pk': item.article.pk, 'revision_id': item.pk})

    def item_pubdate(self, item):
        return item.created_at
