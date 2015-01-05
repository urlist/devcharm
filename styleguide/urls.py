from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from styleguide.views import StyleGuideTemplateView, StyleGuideLandingView, StyleGuideArticleListByTagView, \
    StyleGuideProfileView, StyleGuideArticleView, StyleGuideMyProfileView, StyleGuideMyEmptyProfileView, \
    StyleGuideFullArticleView, StyleGuideFullArticleWikiView, StyleGuideArticleWIPView, StyleGuideArticleUnpublishedView, \
    StyleGuideArticleFormView, StyleGuideTagMenuView


urlpatterns = patterns(
    '',
    url(r'^$', TemplateView.as_view(template_name='styleguide/index.html'), name='styleguide_view_index'),
    url(r'^page/landing$', StyleGuideLandingView.as_view(), name='styleguide_view_articles_home'),
    url(r'^page/tag_menu$', StyleGuideTagMenuView.as_view(), name='styleguide_view_tag_menu'),
    url(r'^page/history$', TemplateView.as_view(template_name='articles/article_history.html'),
        name='styleguide_view_article_history'),
    url(r'^page/profile$', StyleGuideProfileView.as_view(), name='styleguide_view_profile'),
    url(r'^page/my_profile$', StyleGuideMyProfileView.as_view(), name='styleguide_view_my_profile'),
    url(r'^page/empty_profile$', StyleGuideMyEmptyProfileView.as_view(), name='styleguide_view_empty_profile'),
    url(r'^page/tag$', StyleGuideArticleListByTagView.as_view(), name='styleguide_view_articles_tag'),
    url(r'^page/article$', StyleGuideArticleView.as_view(), name='styleguide_view_article'),
    url(r'^page/full_article$', StyleGuideFullArticleView.as_view(), name='styleguide_view_full_article'),
    url(r'^page/full_wiki_article$', StyleGuideFullArticleWikiView.as_view(), name='styleguide_view_full_wiki_article'),
    url(r'^page/wip_article$', StyleGuideArticleWIPView.as_view(), name='styleguide_view_wip_article'),
    url(r'^page/unpublished_article$', StyleGuideArticleUnpublishedView.as_view(),
        name='styleguide_view_unpublished_article'),

    url(r'^page/article_form$', StyleGuideArticleFormView.as_view(), name='styleguide_view_article_form'),

    url(r'^widgets$', TemplateView.as_view(template_name='styleguide/widgets.html'), name='styleguide_widgets'),


    url(r'^template/(?P<template_name>[-_:\w.]+)$', StyleGuideTemplateView.as_view(), name='styleguide_view_template'),
)
