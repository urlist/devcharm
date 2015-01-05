from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.db import models
from django.test import TestCase
from django.test.utils import override_settings
from django_dynamic_fixture import G
from django_webtest import WebTest
from datetime import timedelta
from articles.models import Article
from profiles.models import Author
from scoring.models import ScoreTransaction
from tags.models import Tag


class TestProfileModel(TestCase):
    def test_profile_proxies_some_user_attributes(self):
        user = G(get_user_model())
        author = user.author_profile
        self.assertEqual(user.username, author.username)
        self.assertEqual(user.email, author.email)

    def test_profile_extra_fields(self):
        user = G(get_user_model())
        author = user.author_profile
        self.assertEqual(author.github_profile_url, 'https://github.com/{}'.format(user.username))

        self.assertEqual(author.articles_published_count, 0)
        articles = G(Article, author=user, deleted_at=None, n=3)  # The behavior with deleted articles is unclear, so...
        self.assertEqual(Author.objects.get(pk=author.pk).articles_published_count, 3)
        u2 = G(get_user_model())
        articles[0].author = u2
        articles[0].raw_content = 'changed'
        articles[0].save()
        # A different author shouldn't change the result
        self.assertEqual(Author.objects.get(pk=author.pk).articles_published_count, 3)
        self.assertEqual(u2.author_profile.articles_published_count, 0)  # Sanity check
        self.assertEqual(Author.objects.get(pk=u2.author_profile.pk).edits_count, 1)
        articles[0].author = user
        articles[0].raw_content = 'changed again'
        articles[0].save()
        self.assertEqual(Author.objects.get(pk=author.pk).edits_count, 4)
        # Keeping the same content should not increment the values
        articles[0].save()
        self.assertEqual(Author.objects.get(pk=author.pk).edits_count, 4)
        self.assertEqual(Author.objects.get(pk=author.pk).articles_published_count, 3)  # Sanity check
        # If an article is withdrawn, the count should decrement
        articles[1].published_at = None
        articles[1].save()
        self.assertEqual(Author.objects.get(pk=author.pk).articles_published_count, 2)
        # Finally, kudos
        self.assertEqual(u2.author_profile.kudos_given_count, 0)  # Sanity check
        articles[2].receive_kudos(session_id='something', user=u2)
        self.assertEqual(Author.objects.get(pk=u2.author_profile.pk).kudos_given_count, 1)


class TestProfileView(WebTest):
    def test_profile_view_defaults_to_current_user(self):
        u1, u2 = G(get_user_model(), n=2)
        url = reverse('profiles_profile')
        response = self.app.get(url, user=u1.username)
        self.assertEqual(response.context['author_profile'], u1.author_profile)
        # Anonymous users have no business using this URL, so they receive a Not Found response
        self.app.reset()
        response = self.app.get(url, status=404)
        # Anonymous users can see the (public) profile of an existing user, though
        public_url = reverse('profiles_profile', args=(u2.username, ))
        response = self.app.get(public_url)
        self.assertEqual(response.context['author_profile'], u2.author_profile)
        self.assertTrue(response.context['is_public_profile'])

        # Currently logged in users should be able to see the (public) profile of a different user, of course
        response = self.app.get(public_url, user=u1.username)
        self.assertEqual(response.context['author_profile'], u2.author_profile)
        self.assertTrue(response.context['is_public_profile'])

    @override_settings(PROFILE_PAGE_NUM_SUGGESTED_WIP_ARTICLES=5)
    def test_profile_page_suggests_wip_articles(self):
        u = G(get_user_model())
        url = reverse('profiles_profile')
        response = self.app.get(url, user=u.username)
        # Initially, the list should be empty (no WIP articles)
        self.assertIn('suggested_wip_articles', response.context)
        # If we add a number of wip articles, we expect them to show up
        articles = G(Article, n=5, deleted_at=None)
        for a in articles:
            a.is_wip = True
        response = self.app.get(url, user=u.username)
        self.assertItemsEqual(articles, response.context['suggested_wip_articles'])
        # if we add more articles with high kudos, we expect the first ones to disappear
        articles_with_kudos = G(Article, n=5, received_kudos_count=10, deleted_at=None)
        for a in articles_with_kudos:
            a.is_wip = True
        response = self.app.get(url, user=u.username)
        self.assertItemsEqual(articles_with_kudos, response.context['suggested_wip_articles'])
        # High kudos articles without WIP should not appear
        for a in articles:
            a.received_kudos_count = 20
            a.save()
            a.is_wip = False
        response = self.app.get(url, user=u.username)
        self.assertItemsEqual(articles_with_kudos, response.context['suggested_wip_articles'])

    def test_profile_page_includes_subset_of_the_users_score_history(self):
        u = G(get_user_model())
        url = reverse('profiles_profile')
        transactions = G(ScoreTransaction, user=u, change=5, n=30, fill_nullable_fields=False)
        transactions[0].when = transactions[0].when - timedelta(5)  # Moving this back for the sorting tests
        transactions[0].save()
        transactions[-1].when = transactions[-1].when - timedelta(5)  # Moving this back for the sorting tests
        transactions[-1].save()
        # I'm not sure if this information will be public, so I'm playing it safe and testing the private profile
        response = self.app.get(url, user=u.username)
        self.assertIn('score_history', response.context)
        self.assertEqual(len(response.context['score_history']), settings.PROFILE_PAGE_NUM_SCORE_TRANSACTIONS)
        # It makes sense to also ensure that they are sorted with the most recent on top (to allow for later paging)
        self.assertGreater(response.context['score_history'][0].when, response.context['score_history'][1].when)
        # Also, since 0 and -1 have been moved back, they should not be present
        self.assertNotIn(transactions[0], response.context['score_history'])
        self.assertNotIn(transactions[-1], response.context['score_history'])

    def test_profile_page_includes_recently_created_and_edited_articles(self):
        u = G(get_user_model())
        created = G(Article, n=5, deleted_at=None, author=u)
        url = reverse('profiles_profile')  # We're looking at our own private profile
        response = self.app.get(url, user=u.username)
        self.assertIn('recent_articles_published', response.context)
        self.assertItemsEqual(response.context['recent_articles_published'], created)
        u2 = G(get_user_model())
        for a in created:
            a.author = u2
            a.save()
        response = self.app.get(url, user=u2.username)
        self.assertIn('recent_articles_edited', response.context)
        self.assertItemsEqual(response.context['recent_articles_edited'], created)

    def test_profile_page_includes_own_drafts(self):
        u = G(get_user_model())
        drafts = G(Article, n=5, deleted_at=None, author=u, published_at=None)
        url = reverse('profiles_profile')
        response = self.app.get(url, user=u.username)
        self.assertIn('articles_drafts', response.context)
        self.assertItemsEqual(response.context['articles_drafts'], drafts)
        # Other users should not see the drafts
        self.app.reset()
        response = self.app.get(reverse('profiles_profile', args=(u.username,)))
        self.assertNotIn('articles_drafts', response.context)


class TestScoringModels(WebTest):
    def setUp(self):
        self.user = G(get_user_model(), username='testuser')

    def test_users_receive_points_when_editing_articles(self):
        t = G(Tag)
        a = G(Article, tags=[t], deleted_at=None)
        self.csrf_checks = False
        response = self.app.get(reverse('articles_article_edit', args=(a.pk, )), user=self.user)
        old_score = self.user.author_profile.score
        # We want to do some actual editing here
        response.form['raw_content'] = 'Edited raw content'
        response.form.submit()
        # Expected results are:
        # - The user receives some points;
        # - An audit trail object gets created.
        self.assertEqual(get_user_model().objects.get(pk=self.user.pk).author_profile.score,
                         old_score + settings.ACTIVITY_POINTS['editing_article'])
        self.assertEqual(self.user.scoretransaction_set.latest().operation, 'Edited article {}'.format(a.pk))

    def test_users_receive_points_when_adding_links_to_articles(self):
        t = G(Tag)
        a = G(Article, tags=[t], raw_content="# Some raw content\n\n", deleted_at=None)
        self.csrf_checks = False
        url = reverse('articles_article_edit', args=(a.pk, ))
        response = self.app.get(url, user=self.user)
        old_score = self.user.author_profile.score
        # We want to do some actual editing here
        response.form['raw_content'] = response.form['raw_content'].value + ' http://devcharm.com'
        response.form.submit()
        # Having added a link, we expect the score to be updated accordingly and two score transactions to be created
        new_score = get_user_model().objects.get(pk=self.user.pk).author_profile.score
        self.assertEqual(new_score,
                         old_score + settings.ACTIVITY_POINTS['editing_article']
                         + settings.ACTIVITY_POINTS['adding_links'])
        self.assertEqual(self.user.scoretransaction_set.get(operation__startswith="Added ").operation,
                         'Added 1 link to article {}'.format(a.pk))
        # Adding two links should result in more points
        response = self.app.get(reverse('articles_article_edit', args=(a.pk, )), user=self.user)
        old_score = new_score
        response.form['raw_content'] = response.form['raw_content'].value + ' http://google.com http://nsa.gov'
        response.form.submit()
        new_score = get_user_model().objects.get(pk=self.user.pk).author_profile.score
        self.assertEqual(new_score,
                         old_score + settings.ACTIVITY_POINTS['editing_article']
                         + settings.ACTIVITY_POINTS['adding_links'] * 2)
        self.assertEqual(self.user.scoretransaction_set.get(operation__startswith="Added 2").operation,
                         'Added 2 links to article {}'.format(a.pk))

    def test_users_receive_points_when_creating_articles(self):
        response = self.app.get(reverse('articles_article_create'), user=self.user)
        response.form['raw_content'] = 'Some raw content'
        old_score = self.user.author_profile.score
        response.form.submit()
        new_score = get_user_model().objects.get(pk=self.user.pk).author_profile.score
        self.assertEqual(new_score, old_score + settings.ACTIVITY_POINTS['creating_article'])
        self.assertEqual(self.user.scoretransaction_set.get(operation__startswith="Created").operation,
                         'Created article {}'.format(Article.objects.latest('pk').pk))

        # If, on the other hand, we create a new article with a few links, we should get more points
        response = self.app.get(reverse('articles_article_create'), user=self.user)
        response.form['raw_content'] = 'Some raw content with two https://devcharm.com http://127.0.0.1 links'
        old_score = new_score
        response.form.submit()
        new_score = get_user_model().objects.get(pk=self.user.pk).author_profile.score
        self.assertEqual(new_score,
                         old_score + settings.ACTIVITY_POINTS['creating_article']
                         + settings.ACTIVITY_POINTS['adding_links'] * 2)
        self.assertEqual(self.user.scoretransaction_set.filter(operation__startswith="Created").latest('pk').operation,
                         'Created article {} with 2 links'.format(Article.objects.latest('pk').pk))

    def test_users_are_awarded_points_when_articles_they_have_edited_receive_kudos(self):
        # The basic case is a single author
        a = G(Article, author=self.user)
        old_score = self.user.author_profile.score
        a.receive_kudos(session_id="mysession")
        new_score = get_user_model().objects.get(pk=self.user.pk).author_profile.score
        self.assertEqual(new_score, old_score + settings.ACTIVITY_POINTS['receiving_kudos_as_author'])
        self.assertEqual(self.user.scoretransaction_set.filter(operation__startswith="Received").latest('pk').operation,
                         'Received kudos for article {}'.format(a.pk))
        # Of course, repeating the operation should not result in more points
        old_score = new_score
        a.receive_kudos(session_id="mysession")
        self.assertEqual(new_score, old_score)
        # Testing behavior of editors
        editor = G(get_user_model())
        different_user_old_score = editor.author_profile.score
        a.author = editor
        a.raw_content = 'Something else'  # Otherwise we wouldn't get the revision
        a.save()
        self.assertEqual(a.editors_count, 2)  # Sanity check
        a.receive_kudos(session_id="anothersession")
        # Now both users should have received kudos:
        # - The new editor should receive points for his contribution
        # - while the original author should receive a tenth of the creation bonus
        new_score = get_user_model().objects.get(pk=self.user.pk).author_profile.score
        self.assertEqual(new_score, old_score + settings.ACTIVITY_POINTS['receiving_kudos_as_author'])
        self.assertEqual(get_user_model().objects.get(pk=editor.pk).author_profile.score,
                         different_user_old_score + settings.ACTIVITY_POINTS['receiving_kudos_as_editor'])
        # Clearly, we expect there to be an audit trail for this too:
        self.assertEqual(editor.scoretransaction_set.filter(operation__startswith="Received").latest('pk').operation,
                         'Received kudos for editing article {}'.format(a.pk))
