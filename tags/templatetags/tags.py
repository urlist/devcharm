# -*- coding: utf-8 -*-
from django.template import Library
from django.db.models.loading import get_model
Article = get_model('articles', 'Article')

register = Library()


@register.inclusion_tag('tags/tag_list.html', takes_context=True)
def tags_list(context, css_class=''):
    return {'tags': Article.objects.get_trending_tags, 'css_class': css_class}
