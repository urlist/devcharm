from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, UpdateView
from articles.models import Article
from profiles.models import Author



def track_signup(request):
    redirect_url = '/'
    if 'partial_pipeline' in request.session:
        backend = request.session['partial_pipeline']['backend']
        redirect_url = reverse('social:complete', kwargs={'backend': backend})

    #return redirect(redirect_url + '?signup_success')
    return render(request, 'profiles/track_signup.html', {'redirect_url': redirect_url})


class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ['bio', 'display_name']


class ProfileDetailView(DetailView):
    model = get_user_model()
    template_name = 'profiles/author_detail.html'

    def get_object(self, queryset=None):
        username = self.kwargs.get('username', '')
        if not username:
            if self.request.user.is_authenticated():
                return self.request.user
            raise Http404

        if not queryset:
            queryset = self.get_queryset()
        return get_object_or_404(queryset, username=username)

    def is_public_profile(self):
        """
        Overrideable method for future public profile preview support.

        :return: :rtype: Boolean
        """
        return self.request.user != self.object

    def get_published_articles(self):
        return self.object.created_articles.filter(published_at__isnull=False, deleted_at__isnull=True).order_by('-pk')

    def get_edited_articles(self):
        return self.object.article_set.filter(published_at__isnull=False, deleted_at__isnull=True).order_by('-pk')

    def get_drafts(self):
        return self.object.article_set.filter(published_at__isnull=True, deleted_at__isnull=True).order_by('-pk')

    def get_suggested_wip_articles(self):
        limit = settings.PROFILE_PAGE_NUM_SUGGESTED_WIP_ARTICLES
        return Article.objects.get_wip_articles().order_by('-received_kudos_count')[:limit]

    def get_recent_kudos(self):
        kudoed_articles = self.object.kudos_given.values_list('article', flat=True)
        return Article.objects.filter(pk__in=kudoed_articles)

    def get_context_data(self, **kwargs):
        context_data = super(ProfileDetailView, self).get_context_data(**kwargs)
        context_data['author_profile'] = self.object.author_profile
        context_data['is_public_profile'] = self.is_public_profile()
        context_data['suggested_wip_articles'] = self.get_suggested_wip_articles()
        context_data['recent_articles_published'] = self.get_published_articles()
        context_data['recent_articles_edited'] = self.get_edited_articles()
        context_data['recent_kudos'] = self.get_recent_kudos()
        score_history_limit = settings.PROFILE_PAGE_NUM_SCORE_TRANSACTIONS
        context_data['score_history'] = self.object.scoretransaction_set.order_by('-when')[:score_history_limit]
        if not self.is_public_profile():
            context_data['articles_drafts'] = self.get_drafts()
            context_data['form'] = AuthorForm(instance=self.object.author_profile)
        return context_data


class ProfileEditView(UpdateView):
    model = Author
    fields = ['display_name', 'bio']

    def get_object(self, queryset=None):
        if not self.request.user.is_authenticated():
            raise Http404
        return self.request.user.author_profile

    def form_invalid(self, form):
        # FIXME: I don't know how to return to the main profile view with the
        # form errors. I know it's ugly, but for now we just redirect to the
        # profile again.
        return HttpResponseRedirect(reverse('profiles_profile'))
