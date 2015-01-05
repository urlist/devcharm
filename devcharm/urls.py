from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.sitemaps import GenericSitemap
from django.contrib.sitemaps.views import sitemap
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.core.urlresolvers import reverse
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from articles.models import Article
from articles.views import ArticleListHomepageView
from tags.models import Tag


class TagsSitemap(GenericSitemap):
    def location(self, obj):
        return reverse('articles_list_by_tag', args=(obj.title, ))


sitemaps = {
    'pages': GenericSitemap({
        'queryset': Article.objects.filter(published_at__isnull=False),
        'date_field': 'published_at'
    }, priority=1.0),

    'tags': TagsSitemap({
        'queryset': Tag.objects.all(),
    }, priority=0.5)
}


admin.autodiscover()


urlpatterns = patterns(
    '',  # prefix
    url(r'^admin/', include(admin.site.urls)),  # TDD breach - leaving this in because we won't really test it
    url(r'^$', ArticleListHomepageView.as_view(), name='homepage'),
    url(r'^tags/', include('tags.urls')),
    url(r'^articles/', include('articles.urls')),
    url(r'^profiles/', include('profiles.urls')),
    url(r'^styleguide/', include('styleguide.urls')),
    url(r'^docs/', include('docs.urls')),
    url(r'^login/$', TemplateView.as_view(template_name='login.html'), name='login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}, name='logout'),

    url(r'', include('social.apps.django_app.urls', namespace='social')),

    # The following are required to properly redirect pre_v1 urls
    url(r'^pages/(?P<pk>\d+)$', RedirectView.as_view(pattern_name='articles_article_detail', query_string=True),
        name='OBSOLETE_page-by-id'),
    url(r'^pages/(?P<pk>\d+)-(?P<slug>[-a-z0-9]+)$',
        RedirectView.as_view(pattern_name='articles_article_detail', query_string=True), name='OBSOLETE_page-by-id'),
    url(r'^pages/(?P<pk>\d+)-(?P<slug>[-a-z0-9]+)/history$',
        RedirectView.as_view(pattern_name='articles_article_revision_list', query_string=True),
        name='OBSOLETE_page-history'),

    url(r'sitemap\.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
)

urlpatterns += staticfiles_urlpatterns()  # This checks for DEBUG==True, too
