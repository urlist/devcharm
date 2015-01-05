# -*- coding: utf-8 -*-
import random

from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import Library
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.templatetags.static import static


register = Library()


@register.simple_tag(takes_context=True)
def drilldown_link(context, new_tag):
    query = context['request'].GET.copy()
    drilldown = set(query.getlist('drilldown'))
    drilldown ^= {new_tag}  # Exclusive or on set so that if it's already present it gets removed
    query.setlist('drilldown', drilldown)
    return query.urlencode()


@register.simple_tag(takes_context=True)
def active(context, param, current, default=False, emit='active'):
    value = context['request'].GET.get(param)
    if (not value and default) or (value == current):
        return emit
    return ''


@register.simple_tag()
def group_editors(author, contributors=None, show_first=2):
    def make_link(x):
        if isinstance(x, basestring):
            return x
        else:
            return u'<a href="{}">{}</a>'.format(x.get_absolute_url(), escape(x.display_name or x.username))

    author = author.author_profile
    contributors = list(contributors) if contributors is not None else []
    if not contributors:
        return make_link(author)

    everything = [author] + [c.author_profile for c in contributors]

    tokens = []
    show, group = everything[:show_first], everything[show_first:]
    tokens.extend(show)

    if len(group) == 1:
        tokens.append(u'one other')
    elif len(group) > 1:
        tokens.append(u'{} others'.format(len(group)))

    head = []
    for t in tokens[:-1]:
        head.append(make_link(t))

    head = u', '.join(head)
    tail = u'and {}'.format(make_link(tokens[-1]))

    return mark_safe(' '.join([head, tail]))


@register.filter
def is_editable_by(article, user):
    return article.is_editable_by_user(user)


@register.simple_tag(takes_context=True)
def random_image(context):
    relative = static('images/oldschool/{}.jpg'.format(
        random.randint(0, settings.TOTAL_RANDOM_IMAGES - 1)))
    return context['request'].build_absolute_uri(relative)

