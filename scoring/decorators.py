# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http.response import HttpResponseNotAllowed, HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.decorators import available_attrs
from functools import wraps


def score_change(view_function=None, increment=0, increment_func=None, operation=None):
    """

    @param view_func:
    @param increment: int
    @param increment_func: function
    @param operation: string or function
    @return: @rtype:
    """
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated():
                delta = increment
                if callable(increment_func):
                    delta += increment_func(request)
                if request.user.author_profile.score + delta < 0:  # if it's a decrement, we don't want the view to run
                    return HttpResponseForbidden()
                # We're tracking every single usage of this
                name = operation or view_func.__name__
                if callable(name):
                    name = name(request)
                request.user.scoretransaction_set.create(change=delta, operation=name)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    if view_function:
        return decorator(view_function)
    return decorator


def score_check(view_func, minimum_score=0, redirect_url=None):
    """

    @param view_func:
    @param minimum_score: int
    @param redirect_url: string
    @return: @rtype:
    """

    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated() or request.user.score < minimum_score:
            url = redirect_url or settings.LOGIN_URL
            return redirect(url)
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def score_produce(view_func, change):
    """

    @param view_func:
    @param change: int or function(request)
    @return: @rtype:
    """
    if callable(change):
        return score_change(view_func, increment_func=change)
    return score_change(view_func, increment=change)


def score_consume(view_func, change):
    """

    @param view_func:
    @param change: int or function(request)
    @return: @rtype:
    """
    if callable(change):
        return score_change(view_func, increment_func=change)
    elif change < 0:
        raise ImproperlyConfigured("Score consume decorator requires a positive change or a function")
    return score_change(view_func, increment=-change)