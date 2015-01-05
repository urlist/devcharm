from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt
from articles.feeds import ArticleFeedByTag, ArticleFeedGlobal, RevisionFeed
from articles.views import ArticleDetailView, ArticleCreateView, ArticleUpdateView, ArticleListByTagView, \
    ArticleRevisionListView, ArticlePublishView, give_kudos, ArticleSetDeletedView, ArticleRevisionDiffView


urlpatterns = patterns(
    '',
    url(r'^(?P<pk>\d+)/give_kudos/$', 'articles.views.give_kudos', name='articles_give_kudos_to_article'),
    url(r'^(?P<pk>\d+)/revisions/$', ArticleRevisionListView.as_view(), name='articles_article_revision_list'),
    url(r'^(?P<pk>\d+)-(?P<slug>[-a-z0-9]+)/revisions/$', ArticleRevisionListView.as_view(),
        name='articles_article_revision_list'),
    url(r'^(?P<pk>\d+)-(?P<slug>[-a-z0-9]+)/revisions/feed/$', RevisionFeed(), name='articles_article_revision_feed'),
    url(r'^(?P<pk>\d+)/revisions/feed/$', RevisionFeed(), name='articles_article_revision_feed'),


    url(r'^(?P<pk>\d+)/revisions/(?P<revision_id>\d+)$', ArticleDetailView.as_view(),
        name='articles_article_revision_detail'),
    url(r'^(?P<pk>\d+)/diff_with/(?P<revision_id>\d+)$', ArticleRevisionDiffView.as_view(),
        name='articles_article_revision_diff'),
    url(r'^(?P<pk>\d+)/$', ArticleDetailView.as_view(), name='articles_article_detail'),
    url(r'^(?P<pk>\d+)/(?P<slug>[-a-z0-9]+)/$', ArticleDetailView.as_view(), name='articles_article_detail'),
    url(r'^(?P<pk>\d+)\.md$', ArticleDetailView.as_view(as_source=True), name='articles_article_source'),
    url(r'^edit/(?P<pk>\d+)/$', ArticleUpdateView.as_view(), name='articles_article_edit'),
    url(r'^create/$', ArticleCreateView.as_view(), name='articles_article_create'),
    url(r'^create/(?P<tag>[-a-z0-9]+)/$', ArticleCreateView.as_view(), name='articles_article_create'),
    url(r'^tag/(?P<tag>[-a-z0-9]+)/$', ArticleListByTagView.as_view(), name='articles_list_by_tag'),
    url(r'^feeds/(?P<tag>[-a-z0-9]+)/$', ArticleFeedByTag(), name='articles_feed_by_tag'),
    url(r'^feeds/$', ArticleFeedGlobal(), name='articles_feed_global'),

    url(r'^save/$', csrf_exempt(ArticleCreateView.as_view(restlike=True)), name='articles_article_rest_save'),
    url(r'^save/(?P<pk>\d+)/$',
        csrf_exempt(ArticleUpdateView.as_view(restlike=True)), name='articles_article_rest_save'),
    url(r'^publish/(?P<pk>\d+)/$',
        csrf_exempt(ArticlePublishView.as_view()), name='articles_article_rest_publish'),
    # In this case we have decided to exempt from CSRF the view
    url(r'^kudos/(?P<pk>\d+)/$', csrf_exempt(give_kudos), kwargs={'restlike': True},
        name='articles_article_rest_kudos'),
    url(r'^view/(?P<pk>\d+)/$', 'articles.views.add_article_view', name='articles_article_rest_add_view'),
    url(r'^delete/(?P<pk>\d+)/$', csrf_exempt(ArticleSetDeletedView.as_view()), name='articles_article_rest_delete'),
)
