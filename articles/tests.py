from django.conf import settings
from django.contrib.admin import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse
from django.http import QueryDict, HttpRequest
from django.template import RequestContext
from django.test import TestCase, RequestFactory
from django.utils.html import escape
from django.utils.timezone import now
from django.utils.unittest.case import skip
from django_dynamic_fixture import G, F, N
from datetime import timedelta
from django_webtest import WebTest
from markdown import markdown
from urlparse import urlparse
from articles.admin import ArticleAdmin
from articles.forms import ArticleForm
from articles.models import Article, ArticleGroup, Revision
from tags.models import Tag


class TestArticleSets(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = get_user_model().objects.create_superuser(username='admin', password='password', email='some@ema.il')
        super(TestArticleSets, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.admin.delete()
        super(TestArticleSets, cls).tearDownClass()

    def test_homepage_articles_can_be_aggregated_in_groups(self):
        articles = G(Article, n=2)
        article_group = G(ArticleGroup)
        article_group.articles.add(*articles)
        self.assertIn(article_group, articles[0].articlegroup_set.all())

    def test_article_groups_can_be_retrieved_by_target_block(self):
        article_group = G(ArticleGroup, publish_start=now()-timedelta(1), target_block="some_block")
        self.assertEqual(article_group, ArticleGroup.objects.get_current_for_block("some_block"))

    def test_current_editors_picks_can_be_retrieved_based_on_publish_start(self):
        articles = G(Article, n=2)
        article_group = G(ArticleGroup, publish_start=now()-timedelta(1), target_block="editors_picks")
        article_group.articles.add(*articles)
        self.assertItemsEqual(article_group.articles.all(), ArticleGroup.objects.get_editors_picks(self.admin))
        # Adding a new group with a different publish date
        new_articles = G(Article, n=2)
        second_group = G(ArticleGroup, publish_start=now(), target_block="editors_picks")
        second_group.articles.add(*new_articles)
        self.assertItemsEqual(second_group.articles.all(), ArticleGroup.objects.get_editors_picks(self.admin))
        # Groups with publish_start = None should not be retrieved
        third_group = G(ArticleGroup)
        third_group.articles.add(*articles)
        self.assertItemsEqual(second_group.articles.all(), ArticleGroup.objects.get_editors_picks(self.admin))

    def test_current_promoted_wip_articles_can_be_retrieved(self):
        # "Promoted WIP" should mean articles that are marked as WIP and that belong to a currently
        # published group;
        wip_article = G(Article)
        regular_article = G(Article)
        wip_article.is_wip = True
        wip_group = G(ArticleGroup, publish_start=now()-timedelta(1), target_block='wip')
        wip_group.articles.add(wip_article)
        self.assertItemsEqual(wip_group.articles.all(), ArticleGroup.objects.get_promoted_wip(self.admin))
        # Other published groups should not be involved, of course
        other_group = G(ArticleGroup, publish_start=now()-timedelta(seconds=1))
        other_group.articles.add(regular_article)
        self.assertItemsEqual(wip_group.articles.all(), ArticleGroup.objects.get_promoted_wip(self.admin))


class TestArticleModels(TestCase):
    def test_articles_can_be_set_as_wip_through_property(self):
        # We should have a convenience property to set articles as WIP, seeing as it's used throughout
        a = G(Article, deleted_at=None)
        a.is_wip = True
        self.assertTrue(a.has_tag('wip'))
        # When actually live, we will certainly have a proper wip tag marked as status
        # but, initially, we can't be sure of that - so...
        self.assertEqual(a.tags.get(title='wip').tag_type, 'status')
        # WIP articles should also be marked as wiki
        self.assertTrue(a.is_wiki)
        # We'll also use the same convenience property to mark an article as no longer WIP:
        a.is_wip = False
        self.assertFalse(a.has_tag('wip'))
        # Marking articles as WIP should not cause problems with unsaved articles
        a2 = N(Article, deleted_at=None)
        a2.is_wip = True
        self.assertTrue(Article.objects.get(pk=a2.pk).is_wip)
        # Marking as non-WIP on unsaved articles shouldn't either
        a3 = N(Article)
        a3.is_wip = False  # In this case, we're just happy that no ValueError has been raised

    def test_wip_property_only_acts_on_single_article(self):
        a1, a2 = G(Article, n=2)
        a1.is_wip = True
        a2.is_wip = True
        a1.is_wip = False
        self.assertTrue(a2.is_wip)

    def test_wip_articles_can_be_retrieved_through_manager(self):
        a = G(Article, deleted_at=None)
        a.is_wip = True
        self.assertEqual(Article.objects.get_wip_articles().get(), a)
        wip = a.tags.get()
        articles = G(Article, tags=[wip], n=10, deleted_at=None)
        a.delete()
        self.assertItemsEqual(Article.objects.get_wip_articles(), articles)

    def test_change_title_updates_article_slug(self):
        a = G(Article, deleted_at=None)
        a.title = 'Hello, World!'
        a.save()
        a = Article.objects.get(pk=a.pk)
        self.assertEqual(a.slug, 'hello-world')
        a.title = 'I love cats, I love every kind of cat'
        a.save()
        a = Article.objects.get(pk=a.pk)
        self.assertEqual(a.slug, 'i-love-cats-i-love-every-kind-of-cat')

    def test_marking_articles_as_non_wiki_removes_wip(self):
        a = G(Article)
        a.is_wip = True
        a.is_wiki = False
        a.save()
        self.assertFalse(a.is_wip)

    def test_editable_articles_can_be_retrieved_through_manager(self):
        a1, a2 = G(Article, n=2, deleted_at=None)
        self.assertItemsEqual(Article.objects.get_editable_for_user(a1.author), [a1])
        #admin = G(get_user_model(), is_superuser=True)
        #self.assertItemsEqual(Article.objects.get_editable_for_user(admin), [a1, a2])
        # Wikis can be retrieved by anybody
        a2.is_wiki = True
        a2.save()
        self.assertItemsEqual(Article.objects.get_editable_for_user(a1.author), [a1, a2])

    def generate_hot_articles(self):
        articles = G(Article, n=5, published_at=now(), deleted_at=None)
        articles[3].receive_kudos(session_id='1')
        articles[3].receive_kudos(session_id='2')
        articles[3].receive_kudos(session_id='3')
        articles[4].receive_kudos(session_id='4')
        articles[4].receive_kudos(session_id='5')
        return articles

    def test_articles_can_be_sorted_by_hotness(self):
        articles = self.generate_hot_articles()
        # Since all other articles have 0 karma, we expect [3] to be the first one and [4] to be the second
        self.assertSequenceEqual(articles[3:], Article.objects.sorted_by_hot()[:2])
        # If we change the timestamp on [3] Kudos, we expect its hotness to decay, leaving [4] as first
        articles[3].kudos_received.all().update(timestamp=now()-timedelta(14))  # 2 weeks should be enough
        self.assertEqual(articles[4], Article.objects.sorted_by_hot()[0])
        # If we restore the kudos and change the publish date for 3, we expect the same result
        articles[3].kudos_received.all().update(timestamp=now())
        articles[3].published_at = now()-timedelta(4)  # The break point is around 3.5 days
        articles[3].save()
        self.assertEqual(articles[4], Article.objects.sorted_by_hot()[0])

    def test_old_articles_do_not_cause_underflow(self):
        articles = G(Article, n=5, published_at=now()-timedelta(10000))
        list(Article.objects.sorted_by_hot())  # The query needs to be evaluated

    def test_hotness_sorting_differentiates_between_0_and_1_kudos(self):
        articles = G(Article, n=3, deleted_at=None)
        articles[1].receive_kudos()
        self.assertEqual(articles[1], Article.objects.sorted_by_hot()[0])

    def test_trending_tags_can_be_retrieved(self):
        articles = self.generate_hot_articles()
        articles[0].set_tag('non-hot')
        articles[1].set_tag('non-hot')
        articles[3].set_tag('hot1')
        articles[3].set_tag('hot2')
        articles[4].set_tag('hot2')
        # To avoid using the Tag object directly we'll check for values
        # Please note that, since the list is sorted on an annotated field, the field must be included
        self.assertSequenceEqual([('hot2', 2), ('hot1', 1), ],
                                 Article.objects.get_trending_tags().values_list('title', 'uses_count'))

    def test_articles_is_editable_by_user_method(self):
        author, visitor = G(get_user_model(), n=2)
        a = G(Article, author=author)
        # We want to ensure that the article is not editable by default
        self.assertFalse(a.is_editable_by_user())
        # The author should be able to edit it
        self.assertTrue(a.is_editable_by_user(author))
        # Any other user shouldn't
        self.assertFalse(a.is_editable_by_user(visitor))
        # Unless the article is marked as WIP
        a.is_wiki = True
        a.save()
        self.assertTrue(a.is_editable_by_user(visitor))
        # Or the visitor is a superuser
        a.is_wiki = False
        a.save()
        visitor.is_superuser = True
        visitor.save()
        self.assertTrue(a.is_editable_by_user(visitor))

    def test_articles_primary_tag_can_be_retrieved(self):
        t1 = G(Tag, title="status", tag_type="status")
        t2 = G(Tag, title="cat", tag_type="category")
        t3 = G(Tag, title="tech", tag_type="technology")
        t4 = G(Tag, title="field", tag_type="field")
        # Currently, tech & field should be considered primary
        a = G(Article, tags=[t1, t2, t3, t4, ])
        self.assertEqual(a.primary_tag, t3)
        # If we remove t3, we should get t4
        a.tags.remove(t3)
        self.assertEqual(a.primary_tag, t4)
        # If we remove t4, we're left with no primary tag - this should not cause an error
        a.tags.remove(t4)
        self.assertIsNone(a.primary_tag)

    def test_article_can_count_links_in_its_body(self):
        a = G(Article, raw_content='this article has two links http://devcharm.com and https://127.0.0.1:8000')
        self.assertEqual(a.count_own_links(), 2)
        # This should work for 0 links too
        a.raw_content = 'No links here'
        self.assertEqual(a.count_own_links(), 0)
        # And we should also be able to use the static method directly:
        self.assertEqual(Article.count_links('this article has one link http://devcharm.com'), 1)
        # Duplicate links should not be counted twice
        self.assertEqual(Article.count_links('this article has one link http://devcharm.com http://devcharm.com'), 1)

    def test_articles_have_denormalized_link_count(self):
        a = G(Article, raw_content='this article has two links http://devcharm.com and https://127.0.0.1:8000')
        self.assertEqual(a.links_count, 2)

    def test_saving_articles_renders_html_when_missing(self):
        article = G(Article, title='', description='', rendered_html='',
                    raw_content='# The Title\n\n> The **punchline**\n\nThe **intro**\n\n\n## The rendered HTML')
        # We're explicitly marking title and rendered_html as empty, but they should be populated when rendering
        self.assertHTMLEqual(article.rendered_html, '<h2>The rendered HTML</h2>')
        self.assertEqual(article.title, 'The Title')
        self.assertEqual(article.description, 'The <strong>intro</strong>')
        self.assertEqual(article.punchline, 'The <strong>punchline</strong>')

        # Now, if we remove the description, we still want the rest to work
        article = G(Article, title='', description='', rendered_html='',
                    raw_content='# The Title\n\n> The **punchline**\n\n## The rendered HTML\n\nWith a p')
        self.assertHTMLEqual(article.rendered_html, '<h2>The rendered HTML</h2><p>With a p</p>')
        self.assertEqual(article.title, 'The Title')
        self.assertEqual(article.description, '')
        self.assertEqual(article.punchline, 'The <strong>punchline</strong>')

    def test_deleted_articles_are_only_visible_in_admin(self):
        a = G(Article, deleted_at=now())  # Explicitly setting it as deleted
        self.assertFalse(Article.objects.filter(pk=a.pk).exists())
        self.assertTrue(Article.all_objects.filter(pk=a.pk).exists())
        self.assertIs(Article._default_manager, Article.all_objects)
        self.assertIn(a, ArticleAdmin(Article, AdminSite()).get_queryset(HttpRequest()))

    def test_articles_have_original_creator_field(self):
        a = G(Article)
        u = a.author
        editor = G(get_user_model())
        a.author = editor
        a.save()
        self.assertEqual(a.author, editor)
        self.assertEqual(a.original_author, u)

    def test_all_contributors_are_sorted(self):
        authors = G(get_user_model(), n=6)
        a = G(Article, deleted_at=None, author=authors[3],
              raw_content='# The Title\n\n\nThe intro\n\n\nThe rendered HTML')
        for u in [1, 4, 1, 5]:
            a.raw_content += '\n\nWith extra line {}'.format(u)  # So we save a new version everytime
            a.author = authors[u]
            a.save()
        self.assertSequenceEqual(a.all_contributors, [authors[n] for n in [3, 1, 4, 1, 5]])


class TestArticleKudos(WebTest):
    csrf_checks = False

    def test_users_can_give_kudos_to_an_article(self):
        a = G(Article, deleted_at=None)
        self.assertFalse(a.kudos_received.exists())
        url = reverse('articles_give_kudos_to_article', args=(a.pk, ))
        # This view is not idempotent, so it must be POST-only
        self.app.get(url, status=405)  # Method not allowed

        # When giving kudos as anonymous, the session_id should be saved; since this request does not hit sessions,
        # though, I'll mock it in the headers
        response = self.app.post(url, headers={'Cookie': 'sessionid=fakesessionid;'}, xhr=True)
        # We want to keep the same behaviour that was used in pre_v1 so we expect three things to happen
        # 1. the article's karma should increase by one
        # 2. an audit trail record should be generated (Event model)
        # 3. the response should be the number of kudos received if AJAX
        self.assertEqual(a.received_kudos_count+1, Article.objects.get(pk=a.pk).received_kudos_count)
        self.assertTrue(a.kudos_received.exists())
        kudos_received = a.kudos_received.get()
        # The response should hold the number of kudos received so far
        self.assertEqual(response.body, '1')
        self.assertEqual(kudos_received.session_id, 'fakesessionid')
        self.assertTrue(kudos_received.timestamp)

        # When giving kudos as a logged-in user, on the other hand, the user must be saved
        u = get_user_model().objects.create_user(username='test_user')
        self.app.post(url, user=u.username)
        self.assertTrue(a.kudos_received.filter(user=u).exists())

    def test_a_user_can_only_give_kudos_once(self):
        a = G(Article)
        url = reverse('articles_give_kudos_to_article', args=(a.pk, ))
        u = get_user_model().objects.create_user(username='test_user')
        self.app.post(url, user=u.username, headers={'Cookie': 'sessionid=fakesessionid_1;'})
        self.app.post(url, user=u.username, headers={'Cookie': 'sessionid=fakesessionid_2;'})
        self.assertEqual(a.kudos_received.count(), 1)


class TestArticleViews(WebTest):
    def test_only_author_can_view_unpublished_articles(self):
        u, u2 = G(get_user_model(), n=2)
        #admin = G(get_user_model(), username='admin', is_superuser=True)
        a = G(Article, published_at=None, author=u, deleted_at=None)
        self.app.get(a.get_absolute_url(), status=404)
        # author can see it, of course
        self.app.get(a.get_absolute_url(), status=200, user=u.username)
        # Admins can see it as well
        # self.app.get(a.get_absolute_url(), status=200, user=admin.username)
        # Other users can't
        self.app.get(a.get_absolute_url(), status=404, user=u2.username)
        # Finally, when it's published, everybody can see it
        self.app.reset()
        a.published_at = now()
        a.save()
        self.app.get(a.get_absolute_url(), status=200)

    def test_deleted_articles_do_not_appear_in_normal_views(self):
        u, u2 = G(get_user_model(), n=2)
        admin = G(get_user_model(), username='admin', is_superuser=True)
        a = G(Article, deleted_at=now(), author=u, tags=1)
        self.app.get(a.get_absolute_url(), status=404)
        self.app.get(a.get_absolute_url(), status=404, user=u2.username)
        # Not even authors and admins
        self.app.get(a.get_absolute_url(), status=404, user=u.username)
        self.app.get(a.get_absolute_url(), status=404, user=admin.username)

        # The article shouldn't normally appear in list views either:
        self.app.reset()
        response = self.app.get(reverse('articles_list_by_tag', args=(a.tags.get().title, )))
        self.assertNotIn(a, response.context['article_list'])

        # If we undelete the article, it becomes public again
        self.app.reset()
        a.deleted_at = None
        a.save()
        self.app.get(a.get_absolute_url(), status=200)

    def test_viewing_an_articles_detail_page_increments_its_views(self):
        a = G(Article, deleted_at=None)
        self.assertFalse(a.views_count)
        self.assertFalse(a.articleview_set.count())
        url = reverse('articles_article_detail', args=(a.pk,))
        self.app.get(url)
        # Having seen the page, we expect the following to happen:
        # 1. The article's views_count is incremented
        # 2. An ArticleView object is created for auditing purposes
        self.assertEqual(Article.objects.get(pk=a.pk).views_count, 1)
        self.assertEqual(a.articleview_set.count(), 1)
        # A view as authenticated user should be properly recorded
        u = get_user_model().objects.create_user(username='test_user')
        # We need to remove everything because otherwise the empty session_id causes a caught IntegrityError
        a.articleview_set.all().delete()
        self.app.get(url, user=u.username)
        self.assertTrue(a.articleview_set.filter(user=u).exists())

    def test_views_can_be_incremented_restlike(self):
        a = G(Article)
        url = reverse('articles_article_rest_add_view', args=(a.pk,))
        # This must be a POST-only, admin-only view
        self.app.get(url, status=405)
        self.app.post(url, status=404)  # No anonymous
        u = G(get_user_model())
        self.app.post(url, user=u.username, status=404)  # No regular users
        u.is_superuser = True
        u.save()
        self.assertFalse(a.articleview_set.exists())
        response = self.app.post(url, user=u.username, status=200)  # Admins are allowed
        # The response should include the current number of views
        self.assertEqual(response.body, '1')
        # Sanity check
        self.assertTrue(a.articleview_set.exists())

    def test_refreshing_the_article_page_should_increment_its_views(self):
        a = G(Article, deleted_at=None)
        url = reverse('articles_article_detail', args=(a.pk,))
        # Viewing the page as anon will require checking on sessionid
        self.app.get(url, headers={'Cookie': 'sessionid=fakesessionid;'})
        self.app.get(url, headers={'Cookie': 'sessionid=fakesessionid;'})
        self.assertEqual(a.articleview_set.count(), 2)
        self.assertEqual(Article.objects.get(pk=a.pk).views_count, 2)
        # Viewing the page with different session_id but the same user should result in no increase
        u = get_user_model().objects.create_user(username='test_user')
        a.articleview_set.all().delete()
        self.app.get(url, headers={'Cookie': 'sessionid=fakesessionid_1;'}, user=u.username)
        self.app.get(url, headers={'Cookie': 'sessionid=fakesessionid_2;'}, user=u.username)
        self.assertEqual(a.articleview_set.count(), 2)

    def test_articles_can_be_created(self):
        t = G(Tag)
        u = G(get_user_model())
        url = reverse('articles_article_create')
        # The full editor support should be checked somewhere else; the only thing we expect here is to be able to
        # submit the form and obtain some sort of result
        response = self.app.get(url, user='someuser')
        self.assertIn('form', response.context)
        response.form['raw_content'] = 'random gibberish'
        response = response.form.submit()
        # We expect to be on the new article's detail page
        self.assertTrue(response.json)
        self.assertTrue('random gibberish', Article.objects.get().raw_content)

    @skip("Tags can't be currently selected in form")
    def test_articles_can_be_created_with_default_tag(self):
        t = G(Tag, title="some-tag")
        url = reverse('articles_article_create', kwargs={'tag': t.title})
        # The full editor support should be checked somewhere else; the only thing we expect here is to be able to
        # submit the form and obtain some sort of result
        response = self.app.get(url, user='someuser')
        self.assertEqual(response.form['tags'].value, [str(t.pk)])

    @skip("Editing is currently only REST-based")
    def test_articles_can_be_edited(self):
        article = G(Article, tags=1, deleted_at=None)  # we need to create a tag too
        url = reverse('articles_article_edit', args=(article.pk, ))
        response = self.app.get(url, user=article.author.username)
        self.assertIn('form', response.context)
        response.form['raw_content'] = '# Changed title'
        response = response.form.submit()
        # We expect to be redirected to the article's detail page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Article.objects.get().title, 'Changed title')

    def test_restlike_editing_updates_rendered_html(self):
        article = G(Article, raw_content='# Title\n\n> Punchline\n\nIntro\n\nSome *content*',
                    deleted_at=None, rendered_html='')
        old_rendered_html = article.rendered_html
        data = {'raw_content': '# Changed Title\n\n> New Punchline\n\nAnother Intro\n\nSome fresh *content*'}
        response = self.app.post(reverse('articles_article_rest_save', args=(article.pk,)), params=data,
                                 user=article.author.username)
        refreshed_article = Article.objects.get(pk=article.pk)
        self.assertEqual(data['raw_content'], refreshed_article.raw_content)
        self.assertNotEqual(old_rendered_html, refreshed_article.rendered_html)

    def test_saving_articles_saves_revisions(self):
        article = G(Article, raw_content="Some content")
        self.assertTrue(article.revision_set.exists())
        # Editing the article should result in a new revision while the former remains untouched
        article.raw_content = 'Different raw content'
        article.save()
        self.assertEqual(len(article.revision_set.all()), 2)
        self.assertEqual(article.revision_set.latest().raw_content, 'Different raw content')
        self.assertEqual(article.revision_set.earliest().raw_content, 'Some content')
        # Saving the article without any changes should not result in a new revision, though
        article.save()
        self.assertEqual(len(article.revision_set.all()), 2)
        # Not even by a different author, of course
        article.author = G(get_user_model())
        article.save()
        self.assertEqual(len(article.revision_set.all()), 2)

    def test_article_creation_and_editing_views_require_login(self):
        url = reverse('articles_article_create')
        response = self.app.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.location).path, settings.LOGIN_URL)
        article = G(Article, deleted_at=None)
        url = reverse('articles_article_edit', args=(article.pk, ))
        response = self.app.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.location).path, settings.LOGIN_URL)

    def test_view_specific_article_revision(self):
        article = G(Article, title='article title', description='art desc', rendered_html='123', deleted_at=None)
        rev = G(Revision, article=article, punchline='rev punchline', raw_content='rev content')
        url = reverse('articles_article_revision_detail', kwargs={'pk': article.pk, 'revision_id': rev.pk})
        response = self.app.get(url)
        # We are not going to check for object equality, only contents
        version = response.context['article']
        self.assertEqual(version.title, rev.title)
        self.assertEqual(version.punchline, rev.punchline)
        self.assertEqual(version.description, rev.description)
        self.assertEqual(version.rendered_html, rev.rendered_html)
        self.assertEqual(version.raw_content, rev.raw_content)

    def test_articles_can_be_listed_by_tag(self):
        tag = G(Tag, title='some-tag')
        articles = G(Article, n=2, tags=[tag], deleted_at=None)
        url = reverse('articles_list_by_tag', args=(tag.title, ))
        response = self.app.get(url)
        self.assertIn('article_list', response.context)
        self.assertSequenceEqual(articles, response.context['article_list'])
        # the relevant part is that, if we add another article with a different tag, we don't expect it to show up
        unwanted_article = G(Article, tags=[F(title='a-different-tag')])
        response = self.app.get(url)
        self.assertNotIn(unwanted_article, response.context['article_list'])

    @skip('work in progress articles no longer have dedicated list in tag pages')
    def test_wip_articles_in_tag_pages_have_editorspick_class_when_appropriate(self):
        tag = G(Tag, title='some-tag')
        articles = G(Article, n=2, tags=[tag], deleted_at=None)
        articles[0].is_wip = True
        articles[1].is_wip = True
        wip_group = G(ArticleGroup, publish_start=now()-timedelta(1), target_block='wip')
        wip_group.articles.add(articles[1])
        url = reverse('articles_list_by_tag', args=(tag.title, ))
        response = self.app.get(url)
        self.assertEqual(len(response.html.select('ul.work-in-progress li')), 2)
        # Only one article should have the editor's pick class here
        self.assertEqual(len(response.html.select('ul.work-in-progress li.editors-pick')), 1)
        # The same result should be obtained when the articles are not WIP any longer
        articles[0].is_wip = False
        articles[1].is_wip = False
        response = self.app.get(url)
        self.assertEqual(len(response.html.select('ul.work-in-progress li')), 0)
        self.assertEqual(len(response.html.select('ul.article-list li')), 2)
        # Only one article should have the editor's pick class here
        self.assertEqual(len(response.html.select('ul.article-list li.editors-pick')), 1)

    def test_articles_by_tag_include_related_tags(self):
        t1, t2 = G(Tag, title='first-tag'), G(Tag, title='second-tag')
        G(Tag, title='unused-tag')  # No need to assign this since we can check the items
        articles = G(Article, n=2, deleted_at=None)
        for a in articles:
            a.set_tag(t1)
            a.set_tag(t2)
        url = reverse('articles_list_by_tag', args=(t2.title, ))
        response = self.app.get(url)
        self.assertIn('related_tags', response.context)
        self.assertItemsEqual([t1, t2], response.context['related_tags'])

    def test_articles_by_tag_retrieve_articles_for_related_tags(self):
        t1, t2, t3 = G(Tag, title='first-tag'), G(Tag, title='second-tag'), G(Tag, title='third-tag')
        G(Tag, title='unused-tag')  # No need to assign this since we can check the items
        articles_t1 = G(Article, n=3, tags=[t1], deleted_at=None)
        articles_t2 = G(Article, n=4, tags=[t2], title="deleted")
        articles_t3 = G(Article, n=5, tags=[t3], deleted_at=None, published_at=None, title="draft")
        shared_article = G(Article, tags=[t1, t2, t3], published_at=None, title='shared')  # One is shared with main
        common_article = G(Article, tags=[t2, t3], published_at=None, title='common')  # And one is shared by the others
        url = reverse('articles_list_by_tag', args=(t1.title, ))
        response = self.app.get(url)
        self.assertEqual(len(response.context['related_articles_two']), 0)  # Quick check - articles here are deleted
        self.assertEqual(len(response.context['related_articles_one']), 0)  # and articles here are drafts
        # Update all the articles so that they're visibile
        Article.all_objects.update(published_at=now(), deleted_at=None)
        response = self.app.get(url)
        self.assertEqual(t3, response.context['related_tag_one'])  # Based on number of articles
        self.assertEqual(t2, response.context['related_tag_two'])
        # Now we can check that the articles are correct and that the shared ones are never present in the related lists
        self.assertItemsEqual(articles_t1+[shared_article], response.context['article_list'])
        # The first list will include the shared article with the second one
        self.assertItemsEqual(articles_t3+[common_article], response.context['related_articles_one'])
        # The second one, won't
        self.assertItemsEqual(articles_t2, response.context['related_articles_two'])

    def test_article_detail_retrieves_articles_for_related_tags(self):
        t1, t2, t3 = G(Tag, title='first-tag', type='tech'), G(Tag, title='second-tag',
                                                               type='field'), G(Tag, title='third-tag', type='field')
        G(Tag, title='unused-tag')  # No need to assign this since we can check the items
        articles_t1 = G(Article, n=3, tags=[t1])
        articles_t2 = G(Article, n=4, tags=[t2])
        articles_t3 = G(Article, n=5, tags=[t3])
        shared_article = G(Article, tags=[t1, t2, t3], title='shared')  # One is shared with main
        common_article = G(Article, tags=[t2, t3], title='common')  # And one is shared by the others
        Article.all_objects.update(published_at=now(), deleted_at=None)
        url = reverse('articles_article_detail', args=(articles_t1[0], ))
        response = self.app.get(url)
        self.assertEqual(len(response.context['read_more']), 3)  # two from main + shared
        self.assertItemsEqual(response.context['read_more'], articles_t1[1:] + [shared_article])
        self.assertSequenceEqual([t3, t2], [response.context['related_tag_one'], response.context['related_tag_two']])
        self.assertItemsEqual(response.context['related_articles_one'], articles_t3+[common_article])
        self.assertItemsEqual(response.context['related_articles_two'], articles_t2)

    def test_articles_can_by_filtered_by_multiple_tags(self):
        t1, t2 = G(Tag, title='first-tag'), G(Tag, title='second-tag')
        articles = G(Article, n=2, deleted_at=None)
        for a in articles:
            a.set_tag(t1)
        articles[1].set_tag(t2)
        url = reverse('articles_list_by_tag', args=(t1.title, ))
        response = self.app.get(url+'?drilldown='+t2.title)
        self.assertItemsEqual(response.context['article_list'], [articles[1]])
        # adding a new article with three tags
        t3 = G(Tag, title='third-tag')
        article3 = G(Article, tags=[t1, t2, t3], deleted_at=None)
        response = self.app.get(url+'?drilldown='+t2.title+'&drilldown='+t3.title)
        self.assertItemsEqual(response.context['article_list'], [article3])
        # Removing a tag from the third article should return no results (not an actual use case)
        article3.tags.remove(t2)
        response = self.app.get(url+'?drilldown='+t2.title+'&drilldown='+t3.title)
        self.assertFalse(response.context['article_list'])

    def test_revision_list_shows_revisions_for_article(self):
        a = G(Article, deleted_at=None)
        url = reverse('articles_article_revision_list', args=(a.pk, ))
        response = self.app.get(url)  # This should be public, I suppose?
        self.assertIn('revision_list', response.context)
        self.assertEqual(response.context['current_version'], a)
        # Initially, this should be populated with one item - the original version
        self.assertEqual(len(response.context['revision_list']), 1)
        # If we add revisions, we want them to show up...
        revs = G(Revision, article=a, n=3)
        response = self.app.get(url)
        self.assertEqual(len(response.context['revision_list']), 4)
        # ...but only if they are for the current article
        nonrevs = G(Revision, n=3)
        response = self.app.get(url)
        self.assertNotIn(nonrevs, response.context['revision_list'])

    def test_revisions_can_be_diffed_against_current(self):
        article = G(Article, raw_content='# This is the title\n\nThis is the description with removed content',
                    deleted_at=None, rendered_html='')
        article.raw_content = '# This is the changed title\n\nThis is the description\n\nThis is the added content'
        article.rendered_html = ''
        article.save()
        url = reverse('articles_article_revision_diff', args=(article.pk, article.revision_set.earliest('pk').pk))
        response = self.app.get(url)
        self.assertTemplateUsed(response, 'articles/revision_diff.html')
        # We expect to receive the two objects in the context
        self.assertIsInstance(response.context['object'], Article)
        self.assertIsInstance(response.context['revision'], Revision)
        # What's more important, we expect there to be a diff
        self.assertIn('diff', response.context)
        # The diff should be a list of 3-tuples with (status, left, right)
        self.assertEqual(len(response.context['diff']), 5)  # There are five lines -- three content and two empty lines

    def test_saving_articles_increments_editors_and_revisions_count(self):
        a = G(Article)
        first_author = a.author
        self.assertFalse(a.revisions_count)
        # Initially we just want to check that the revisions count is properly increased when a new revision is saved
        a.raw_content = 'Different raw content'
        previous_revisions_count = a.revisions_count
        a.save()
        self.assertEqual(previous_revisions_count+1, a.revisions_count)
        # When saving does not create a new revision, the count is left untouched
        a.save()
        self.assertEqual(previous_revisions_count+1, a.revisions_count)

        # When an article is saved by a different user, we want the editors_count to be incremented too
        self.assertEqual(a.editors_count, 1)
        u = G(get_user_model())
        a.author = u
        a.raw_content = 'Different again'
        a.save()
        self.assertEqual(previous_revisions_count+2, a.revisions_count)  # sanity check
        self.assertEqual(a.editors_count, 2)
        # Saving again with the previous user should not increment the editors count.
        a.author = first_author
        a.raw_content = 'And again'
        a.save()
        self.assertEqual(previous_revisions_count+3, a.revisions_count)  # sanity check
        self.assertEqual(a.editors_count, 2)

    def test_article_create_update_views_use_correct_form(self):
        url = reverse('articles_article_create')
        response = self.app.get(url, user='someuser')
        self.assertTrue(isinstance(response.context['form'], ArticleForm))


class TestArticleTemplateTags(WebTest):
    def test_drilldown_links_templatetag(self):
        from articles.templatetags.articles import drilldown_link
        path = reverse('articles_list_by_tag', args=('tag1', ))
        request = RequestFactory().get(path)
        context = RequestContext(request)
        result = drilldown_link(context, 'tag2')
        self.assertItemsEqual(QueryDict(result).getlist('drilldown'), ['tag2'])
        # Now, using the already processed result, we want to add a second tag
        request = RequestFactory().get(path+'?'+result)
        context = RequestContext(request)
        result = drilldown_link(context, 'tag3')
        self.assertItemsEqual(QueryDict(result).getlist('drilldown'), ['tag2', 'tag3'])
        # Passing the same tag a second time should remove it
        request = RequestFactory().get(path+'?'+result)
        context = RequestContext(request)
        result = drilldown_link(context, 'tag2')
        self.assertItemsEqual(QueryDict(result).getlist('drilldown'), ['tag3'])

    def test_check_editable(self):
        # we could probably skip this and have a better test using Mock but it's not worth the hassle, I think
        from articles.templatetags.articles import is_editable_by
        author, visitor, superuser = G(get_user_model(), n=3)
        article = G(Article, author=author, deleted_at=None)
        # Articles shouldn't normally be considered editable by anon users
        self.assertFalse(is_editable_by(article, AnonymousUser()))
        self.assertFalse(is_editable_by(article, visitor))
        self.assertTrue(is_editable_by(article, author))
        # Articles should also be editable when marked as wiki and when the visitor is a superuser
        superuser.is_superuser = True
        superuser.save()
        self.assertTrue(is_editable_by(article, superuser))
        article.is_wiki = True
        article.save()
        self.assertTrue(is_editable_by(article, visitor))
        # Finally, when an article is marked as wiki it should be considered "editable" even from anon users,
        # but they will have to login before the actual editing
        self.assertTrue(is_editable_by(article, AnonymousUser()))

    def test_group_editors(self):
        from articles.templatetags.articles import group_editors
        def make_link(x):
            x = x.author_profile
            return '<a href="{}">{}</a>'.format(x.get_absolute_url(), escape(x.display_name or x.username))

        # Since is not so simple to generate Authors, we generate Users instead. We are using the __unicode__ method
        # that is in both Models. Keep calm and KISS.
        editors = G(get_user_model(), n=10)
        author, contributors = editors[0], editors[1:]
        # First case, we have just one element to display
        s = make_link(author)
        self.assertEqual(group_editors(author), s)
        # Second case, we have two element to display
        s = '{} and {}'.format(make_link(author), make_link(contributors[0]))
        self.assertEqual(group_editors(author, [contributors[0]]), s)
        # Third case, we have two element and one other to display
        s = '{}, {} and one other'.format(make_link(author), make_link(contributors[0]))
        self.assertEqual(group_editors(author, contributors[:2]), s)
        # Fourth case, we have many elements to display
        s = '{}, {} and 8 others'.format(make_link(author), make_link(contributors[0]))
        self.assertEqual(group_editors(author, contributors), s)
        # Other test
        s = '{}, {}, {} and 7 others'.format(make_link(author), make_link(contributors[0]), make_link(contributors[1]))
        self.assertEqual(group_editors(author, contributors, 3), s)

    def test_active_templatetag(self):
        from articles.templatetags.articles import active
        path = reverse('articles_list_by_tag', args=('tag1', )) + '?sort=view'
        request = RequestFactory().get(path)
        context = RequestContext(request)
        self.assertEqual(active(context, 'sort', 'view'), 'active')
        self.assertEqual(active(context, 'sort', 'hot'), '')

        path = reverse('articles_list_by_tag', args=('tag1', ))
        request = RequestFactory().get(path)
        context = RequestContext(request)
        self.assertEqual(active(context, 'sort', 'view', default=True), 'active')
        self.assertEqual(active(context, 'sort', 'hot'), '')


class TestArticleForm(TestCase):
    def setUp(self):
        super(TestArticleForm, self).setUp()
        self.sample_meta = """# Header title
> blockquote punchline


Paragraph introduction **markup**.
"""
        self.sample_content = """## First section

- [Link title](http://example.com/) is an example of title.
- [Devcharm](http://devcharm.com) is quite a nice place.
"""
        self.user = G(get_user_model(), username="test_username")

    def test_articleform_transforms_rawcontent_to_fields_to_allow_saving(self):
        raw_content = self.sample_meta + self.sample_content
        form = ArticleForm(data={'author': self.user.pk, 'raw_content': raw_content})
        self.assertTrue(form.is_valid())
        # First, we check that the form has parsed the markdown
        data = form.cleaned_data
        self.assertIn('full_rendered_content', data)
        self.assertEqual(markdown(raw_content), data['full_rendered_content'])
        # Now the splits:
        # The first is the title
        self.assertEqual('Header title', data['title'])
        # Then the punchline
        self.assertEqual('blockquote punchline', data['punchline'])
        # The introduction should keep the formatting, on the other hand.
        self.assertEqual('Paragraph introduction <strong>markup</strong>.', data['description'])
        # At this point, we should have the actual body of the article left as rendered_html.
        self.assertHTMLEqual(markdown(self.sample_content), data['rendered_html'])
