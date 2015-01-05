from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseNotAllowed
from django.http.response import HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect
from django.template import loader
from django.template.loader import get_template
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView, ListView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import ProcessFormView, ModelFormMixin
import json
from articles.diff import side_by_side_diff
from articles.forms import ArticleForm
from articles.models import Article, ArticleGroup, Revision
from tags.models import Tag


@require_POST
def give_kudos(request, pk, restlike=False):
    article = get_object_or_404(Article, pk=pk)
    request_user = None
    if request.user.is_authenticated():
        request_user = request.user
    current_kudos = article.receive_kudos(session_id=request.COOKIES.get(settings.SESSION_COOKIE_NAME, ''),
                                          user=request_user)
    if restlike or request.is_ajax():
        return HttpResponse(current_kudos)
    nxt = request.POST.get('next', '/')
    return redirect(nxt)


@csrf_exempt
@require_POST
def add_article_view(request, pk):
    if not request.user.is_authenticated() or not request.user.is_superuser:
        return HttpResponseNotFound()
    article = get_object_or_404(Article, pk=pk)
    article.receive_view(request.COOKIES.get(settings.SESSION_COOKIE_NAME, ''), user=request.user)
    return HttpResponse(article.views_count+1)  # The Article instance is no longer updated in the method, so...


class ArticleDetailView(DetailView):
    model = Article
    as_source = False

    def get_queryset(self):
        return Article.objects.get_queryset_for_user(self.request.user)

    def get(self, request, *args, **kwargs):
        response = super(ArticleDetailView, self).get(request, *args, **kwargs)
        request_user = None
        if request.user.is_authenticated():
            request_user = request.user
        self.object.receive_view(session_id=request.COOKIES.get(settings.SESSION_COOKIE_NAME, ''),
                                 user=request_user)
        return response

    def get_related_context_data(self, main_tag):
        context_data = {}
        queryset_for_user = Article.objects.get_queryset_for_user(self.request.user)
        # Other articles with the same primary tag
        read_more = queryset_for_user.filter(tags=main_tag).exclude(pk=self.object.pk)
        context_data['read_more'] = read_more
        # related tags and articles depend on the main tag
        related_tags = Article.objects_as_tagged.get_tags_by_count(read_more).exclude(title=main_tag.title)
        alt_primary_related_tags = related_tags.exclude(tag_type=main_tag.tag_type).filter(
            tag_type__in=Tag.PRIMARY_TYPES)
        padding_tags = list(Article.objects_as_tagged.get_tags_by_count().exclude(title=main_tag.title).exclude(
            title__in=alt_primary_related_tags.values_list('title', flat=True)))
        # Since we need to run it twice, it makes sense to evaluate it once
        alt_primary_related_tags = list(alt_primary_related_tags)
        try:
            context_data['related_tag_one'] = (alt_primary_related_tags + padding_tags)[0]
        except IndexError:
            pass
        else:
            context_data['related_articles_one'] = queryset_for_user.filter(
                tags=context_data['related_tag_one']).exclude(pk__in=read_more.values_list('pk', flat=True))
            try:
                context_data['related_tag_two'] = (alt_primary_related_tags + padding_tags)[1]
            except IndexError:
                pass
            else:
                context_data['related_articles_two'] = queryset_for_user.filter(
                    tags=context_data['related_tag_two']).exclude(
                        pk__in=read_more.values_list('pk', flat=True)).exclude(
                            pk__in=context_data['related_articles_one'].values_list('pk', flat=True))
        return context_data

    def get_context_data(self, **kwargs):
        context_data = super(ArticleDetailView, self).get_context_data(**kwargs)
        if 'revision_id' in self.kwargs:
            revision = get_object_or_404(self.object.revision_set, pk=self.kwargs['revision_id'])
            revision_data = model_to_dict(revision, ['title', 'punchline', 'description', 'rendered_html',
                                                     'raw_content'])
            for key, value in revision_data.items():
                setattr(context_data['article'], key, value)
        context_data['read_more'] = Article.objects.none()
        context_data['related_tag_one'] = None
        context_data['related_articles_one'] = Article.objects.none()
        context_data['related_tag_two'] = None
        context_data['related_articles_two'] = Article.objects.none()
        context_data['canonical_url'] = self.request.build_absolute_uri(self.object.get_canonical_url())
        main_tag = context_data['object'].primary_tag
        if main_tag is not None:
            context_data.update(self.get_related_context_data(main_tag))
        return context_data

    def render_to_response(self, context, **response_kwargs):
        if self.as_source:
            # Alternatively, we could use 'text/x-markdown; charset=utf-8' here, which would make sense and
            # help hypothetical Markdown-aware browsers/plugins.
            return HttpResponse(self.object.raw_content, content_type='text/plain; charset=utf-8')
        return super(ArticleDetailView, self).render_to_response(context, **response_kwargs)


class ScoreTrackingMixin(View):
    def award_points(self, delta, operation_description):
        self.request.user.scoretransaction_set.create(change=delta, operation=operation_description)


class RESTLikeMixin(ModelFormMixin):
    restlike = False

    def form_valid(self, form):
        response = super(RESTLikeMixin, self).form_valid(form)
        if self.restlike:  # In this case, the required output is the PK of the created object and its URL as JSON.
            # Calling super.form_valid() is necessary to save the object, anyway
            response_data = {'pk': self.object.pk,
                             'url': self.object.get_absolute_url(),
                             'edit_url': self.object.get_edit_url(),
                             'save_url': self.object.get_save_url(),
                             'publish_url': self.object.get_publish_url(),
                             'delete_url': self.object.get_delete_url()}
            return HttpResponse(json.dumps(response_data, ensure_ascii=False), content_type='application/json')
        return response


class InjectAuthorMixin(ModelFormMixin, View):
    def get_form_kwargs(self):
        kwargs = super(InjectAuthorMixin, self).get_form_kwargs()
        data = kwargs.get('data')
        if data is not None:
            data = data.copy()
            data['author'] = self.request.user.pk
            kwargs['data'] = data
        return kwargs


class ArticleCreateView(RESTLikeMixin, InjectAuthorMixin, CreateView, ScoreTrackingMixin):
    model = Article
    form_class = ArticleForm

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(ArticleCreateView, self).dispatch(request, *args, **kwargs)

    def get_article_template(self):
        return loader.render_to_string('articles/article_template.md')

    def get_initial(self):
        initial = super(ArticleCreateView, self).get_initial()
        tag = self.kwargs.get('tag')
        if tag:
            initial['tags'] = [get_object_or_404(Tag, title=tag)]
        initial['raw_content'] = self.get_article_template()
        return initial

    def form_valid(self, form):
        response = super(ArticleCreateView, self).form_valid(form)
        if self.request.user.is_authenticated():
            links = self.object.links_count
            bonus_points = settings.ACTIVITY_POINTS['adding_links'] * links
            operation = 'Created article {}'.format(self.object.pk)
            if links > 0:
                operation += ' with {links_count} link{s}'.format(links_count=links, s='s' if links > 1 else '')
            self.award_points(settings.ACTIVITY_POINTS['creating_article'] + bonus_points, operation)
        return response


class ArticleUpdateView(RESTLikeMixin, InjectAuthorMixin, UpdateView, ScoreTrackingMixin):
    model = Article
    previous_links = 0
    form_class = ArticleForm

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(ArticleUpdateView, self).dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = super(ArticleUpdateView, self).get_object(queryset)
        self.previous_links = obj.count_own_links()
        return obj

    def form_valid(self, form):
        response = super(ArticleUpdateView, self).form_valid(form)
        if self.request.user.is_authenticated():
            self.award_points(settings.ACTIVITY_POINTS['editing_article'], 'Edited article {}'.format(self.object.pk))
            link_diff = self.object.links_count - self.previous_links
            if link_diff > 0:
                points = settings.ACTIVITY_POINTS['adding_links'] * link_diff
                self.award_points(points,
                                  'Added {links_count} link{s} to article {pk}'.format(links_count=link_diff,
                                                                                       pk=self.object.pk,
                                                                                       s='s' if link_diff > 1 else ''))
        return response


class RESTLikeUpdateView(RESTLikeMixin, UpdateView):
    object = None
    restlike = True

    def get_queryset(self):
        if self.request.user.is_superuser:
            return super(RESTLikeUpdateView, self).get_queryset()
        return super(RESTLikeUpdateView, self).get_queryset().filter(author=self.request.user)

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        # We don't care about the form validation here - the simple POST is considered enough
        return self.form_valid(self.get_form(self.get_form_class()))


class ArticlePublishView(RESTLikeUpdateView):
    model = Article
    fields = ['published_at']

    def get_form_kwargs(self):
        kwargs = super(ArticlePublishView, self).get_form_kwargs()
        kwargs['data'] = {'published_at': self.object.published_at or now()}
        return kwargs


class ArticleSetDeletedView(RESTLikeUpdateView):
    model = Article
    fields = ['deleted_at']

    def get_form_kwargs(self):
        kwargs = super(ArticleSetDeletedView, self).get_form_kwargs()
        kwargs['data'] = {'deleted_at': self.object.deleted_at or now()}
        return kwargs

    def post(self, request, *args, **kwargs):
        if not self.request.user.is_authenticated():
            return HttpResponseForbidden()
        return super(ArticleSetDeletedView, self).post(request, *args, **kwargs)


class ArticleListView(ListView):
    model = Article
    context_object_name = 'article_list'

    def get_queryset(self):
        sort_key = self.request.GET.get('sort')
        base_qs = Article.objects.get_queryset_for_user(self.request.user)
        if sort_key == 'new':
            qs = base_qs.order_by('-published_at')
        elif sort_key == 'views':
            qs = base_qs.order_by('-views_count')
        elif sort_key == 'kudos':
            qs = base_qs.order_by('-received_kudos_count')
        elif sort_key == 'last_edited':
            qs = base_qs.order_by('-updated_at')
        else:
            qs = Article.objects.sorted_by_hot(base_qs)
        return qs


class ArticleListByTagView(ArticleListView):
    main_tag = None

    def get_queryset(self):
        self.main_tag = self.kwargs.get('tag')
        qs = super(ArticleListByTagView, self).get_queryset().filter(tags__title=self.main_tag)
        drilldown = [t for t in self.request.GET.getlist('drilldown') if t != self.main_tag]
        for tag in drilldown:
            qs = qs.filter(tags__title=tag)
        return qs

    def get_related_lists_context_data(self, context_data, main_pks, queryset_for_user):
        related_lists = {
            'related_tag_one': None,
            'related_tag_two': None,
            'related_articles_one': Article.objects.none(),
            'related_articles_two': Article.objects.none(),
        }
        related_tags = list(context_data['related_tags'].exclude(title=self.main_tag))
        if related_tags:
            related_lists['related_tag_one'] = related_tags[0]
            related_list_one = queryset_for_user.filter(tags=related_lists['related_tag_one']).exclude(pk__in=main_pks)
            related_lists['related_articles_one'] = related_list_one
            if len(related_tags) > 1:
                related_lists['related_tag_two'] = related_tags[1]
                third_list_exclusions = main_pks + list(related_list_one.values_list('pk', flat=True))
                related_list_two = queryset_for_user.filter(tags=related_lists['related_tag_two']).exclude(
                    pk__in=third_list_exclusions)
                related_lists['related_articles_two'] = related_list_two
        return related_lists

    def get_context_data(self, **kwargs):
        context_data = super(ArticleListByTagView, self).get_context_data(**kwargs)
        article_list = context_data['article_list']

        # The following is not pretty but I see no other way of ensuring all the tags are present, since we're
        # filtering on the tag in the main queryset
        # Also: note that evaluating the queryset here avoids hitting the DB again later on
        queryset_for_user = Article.objects.get_queryset_for_user(self.request.user)
        main_pks = list(article_list.values_list('pk', flat=True))  # Evaluate once
        context_data['related_tags'] = Article.objects_as_tagged.get_tags_by_count(
            queryset_for_user.filter(pk__in=main_pks))

        wip = self.get_queryset().filter(tags__title=Tag.WIP_TAG)
        context_data['wip_articles'] = wip

        # FIXME: I am not loving this way of removing the articles preent in the WIP list; refactor ASAP.
        context_data['article_list'] = article_list.exclude(pk__in=wip.values_list('pk', flat=True))
        context_data['main_tag'] = self.main_tag

        related_lists = self.get_related_lists_context_data(context_data, main_pks, queryset_for_user)
        context_data.update(related_lists)
        return context_data


class ArticleListHomepageView(ArticleListView):
    template_name = 'landing.html'

    def get_context_data(self, **kwargs):
        context_data = super(ArticleListHomepageView, self).get_context_data(**kwargs)
        context_data['editors_picks'] = ArticleGroup.objects.get_editors_picks(self.request.user)
        context_data['wip_articles'] = ArticleGroup.objects.get_promoted_wip(self.request.user)
        context_data['new_articles'] = Article.objects.get_queryset_for_user().order_by('-published_at')
        context_data['trending_tags'] = Article.objects.get_trending_tags()
        return context_data


class ArticleRevisionListView(ListView):
    model = Revision
    main_object = None

    def get_queryset(self):
        return self.main_object.revision_set.all()

    def get(self, request, *args, **kwargs):
        self.main_object = get_object_or_404(Article.objects.get_queryset_for_user(self.request.user),
                                             pk=self.kwargs.get('pk'))
        return super(ArticleRevisionListView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context_data = super(ArticleRevisionListView, self).get_context_data(**kwargs)
        context_data['current_version'] = self.main_object
        return context_data


class ArticleRevisionDiffView(DetailView):
    model = Article
    template_name = 'articles/revision_diff.html'
    revision = None

    def get_object(self, queryset=None):
        obj = super(ArticleRevisionDiffView, self).get_object(queryset)
        self.revision = get_object_or_404(obj.revision_set, pk=self.kwargs['revision_id'])
        return obj

    def get_context_data(self, **kwargs):
        context_data = super(ArticleRevisionDiffView, self).get_context_data(**kwargs)
        context_data['article'] = self.revision.article
        context_data['revision'] = self.revision
        context_data['diff'] = list(side_by_side_diff(self.revision.raw_content, self.object.raw_content))
        return context_data
