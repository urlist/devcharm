# -*- coding: utf-8 -*-
# Project-level acceptance tests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.utils.timezone import now
from django.utils.unittest.case import skip
from django_dynamic_fixture import G
from django_webtest import WebTest
from datetime import timedelta
from urlparse import urlparse
from articles.models import Article, ArticleGroup, Kudos
from tags.models import Tag


class DevcharmContentTest(WebTest):
    def assertTitlesEqual(self, response, items, ul_class):
        self.assertItemsEqual([item.title for item in items],
                              [element.string for element in response.html.select('ul.{} li h4 a'.format(ul_class))])


class TestHomePageContent(DevcharmContentTest):
    def test_homepage_shows_hand_picked_articles(self):
        index_url = reverse('homepage')
        response = self.app.get(index_url)
        # TDD Breach: Of course, the page must inherit from base.html; we should check more thoroughly for that but
        # I'll settle for this:
        self.assertTemplateUsed(response, '_baseline.html')

        # We expect the page to be able to show an editor's picks section with a set of lists
        self.assertIn('editors_picks', response.context)
        self.assertTrue(response.html.select('ul.featured'))

        # No decision has been made yet regarding the interface that will be used to select articles so, for the moment
        # I will use fixtures here.
        article1 = G(Article, title='First article')
        article2 = G(Article, title='Second article')
        editorspicks = G(ArticleGroup, publish_start=now() - timedelta(1), deleted_at=None)
        editorspicks.articles.add(article1)
        secondpicks = G(ArticleGroup, publish_start=None, deleted_at=None)  # Otherwise DDF will fill_nullable_fields
        secondpicks.articles.add(article2)
        response = self.app.get(index_url)
        featured = response.html.find('ul', class_='featured')
        self.assertIn('First article', featured.text)
        self.assertNotIn('Second article', featured.text)
        # If we change the publishing timeframes for the groups, we expect the second to be visibile
        editorspicks.save()
        secondpicks.publish_start = now() - timedelta(seconds=1)
        secondpicks.save()
        response = self.app.get(index_url)
        featured = response.html.find('ul', class_='featured')
        self.assertNotIn('First article', featured.text)
        self.assertIn('Second article', featured.text)

    def test_homepage_shows_wip_articles(self):
        index_url = reverse('homepage')
        article1 = G(Article, title='First article', deleted_at=None)
        article2 = G(Article, title='Second article', deleted_at=None)
        # Neither article is WIP, nor is included in a group, so we expect them to only appear in the generated list
        # and in the list with the new articles
        response = self.app.get(index_url)
        self.assertEqual(len(response.html.find_all(text='First article')), 2)
        # Now, we need two groups: editor's picks and WIP articles
        editorspicks = G(ArticleGroup)
        editorspicks.articles.add(article1)
        wip = G(ArticleGroup, target_block='wip')
        wip.articles.add(article2)
        # We expect them both to appear under a different heading
        response = self.app.get(index_url)
        self.assertTrue(response.html.select('.wiki-lists ul'))
        # We expect the context to hold editor's picks too, but that's covered elsewhere
        self.assertIn('wip_articles', response.context)
        self.assertIn(article2, response.context['wip_articles'])
        # We also expect the content to be actually visible, of course
        self.assertIn('Second article', response.body)

    def generate_hot_articles(self):
        articles = G(Article, n=5, published_at=now() - timedelta(1), deleted_at=None)
        for i, a in enumerate(articles):
            a.title = ['First', 'Second', 'Third', 'Fourth', 'Fifth'][i]
            a.save()
            for j in range(0, i + 1):  # We need at least one kudos for every article for them to show up in the list
                a.receive_kudos(session_id='fakesession_{}'.format(j))
        return articles

    @skip('Sorting is not currently enabled for non-ed articles in homepage')
    def test_homepage_shows_a_non_editorialized_subset_of_articles(self):
        # Beyond editors' picks and WIP highlights, there is a third set of articles, generated on the fly
        # The initial view is based on the articles' "hotness" rating.
        index_url = reverse('homepage')
        articles = self.generate_hot_articles()
        response = self.app.get(index_url)
        self.assertTrue(response.html.select('ul.article-list'))
        self.assertIn('article_list', response.context)
        self.assertSequenceEqual(response.context['article_list'], articles[::-1])
        articles_by_hotness = response.html.select('ul.article-list li.article')
        self.assertIn('Fifth', articles_by_hotness[0].text)
        # Clicking on the actual link should yield the same results
        response = response.click('hot', href='\?sort=hot')
        self.assertSequenceEqual(articles_by_hotness, response.html.select('ul.article-list li.article'))

        # The same page should be able to return a different subset, sorted by date descending - adding two should
        # be enough
        new_articles = G(Article, n=2, deleted_at=None)
        response = response.click('new', href='\?sort=new')
        self.assertSequenceEqual(response.context['article_list'][:2], new_articles)

        # The page should also show a subset based on views count
        articles[1].receive_view()
        articles[2].receive_view()
        articles[2].receive_view(session_id='different_session_id')
        response = response.click('views', href='\?sort=views')
        self.assertSequenceEqual(response.context['article_list'][:2], [articles[2], articles[1]])

        # We also expect one on pure kudos (as opposed to hotness)
        Article.objects.all().update(received_kudos_count=0)
        Kudos.objects.all().delete()
        kudoed_articles = list(Article.objects.all()[1:3])
        kudoed_articles[0].receive_kudos()
        kudoed_articles[0].receive_kudos(session_id='different_session_id')
        kudoed_articles[1].receive_kudos()
        response = response.click('kudos', href='\?sort=kudos')
        self.assertSequenceEqual(response.context['article_list'][:2], kudoed_articles)

        # Finally, one sorted by updated_at
        Article.objects.all().update(updated_at=now() - timedelta(1))
        articles[3].updated_at = now() - timedelta(hours=1)
        articles[3].save()
        articles[4].updated_at = now()
        articles[4].save()
        response = response.click('last edited', href='\?sort=last_edited')
        self.assertSequenceEqual(response.context['article_list'][:2], [articles[4], articles[3]])

    @skip("Trending tags are not visibile yet")
    def test_homepage_includes_trending_tags(self):
        index_url = reverse('homepage')
        # First we can check for the existance of an UL and the context data
        response = self.app.get(index_url)
        self.assertIn('trending_tags', response.context)
        self.assertTrue(response.html.select('ul.trending-tags'))
        # The requirement for a tag to be considered "trending" is that it's present in one of the hot articles
        articles = self.generate_hot_articles()  # the last one is certainly the hottest
        for a in articles:
            a.set_tag('hot-tag')
        # The end result should be that we have 'sampletag' as first trending
        response = self.app.get(index_url)
        self.assertIn('hot-tag', response.html.select('ul.trending-tags li.tag')[0].text)
        # Other tags that have not been associated with hot articles should not show up, though
        t = G(Tag, title='non hot tag')
        response = self.app.get(index_url)
        self.assertNotIn(t, response.context['trending_tags'])

    def test_homepage_allows_users_to_start_a_new_article(self):
        index_url = reverse('homepage')
        response = self.app.get(index_url, user="loggedinuser")
        response = response.click('Write a post')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'articles/article_form.html')

    def test_homepage_should_have_rss_feed(self):
        url = reverse('homepage')
        response = self.app.get(url)
        feed_link = response.html.find('link', attrs={'rel': 'alternate'})
        self.assertTrue(feed_link)
        G(Article, n=3, deleted_at=None, published_at=None)
        response = self.app.get(feed_link['href'], status=200)
        channel = response.xml.find('./channel')
        self.assertEqual(channel.find('title').text, 'Recent pages')
        self.assertEqual(channel.find('description').text, 'New articles from Devcharm')
        self.assertEqual(urlparse(channel.find('link').text).path, reverse('articles_feed_global'))
        # Since the articles have not been published yet, they should not show up
        self.assertEqual(len(response.xml.findall('./channel/item')), 0)
        Article.objects.all().update(published_at=now())
        response = self.app.get(feed_link['href'], status=200)
        self.assertEqual(len(response.xml.findall('./channel/item')), 3)


class TestArticleListContent(DevcharmContentTest):
    def test_articles_can_be_listed_by_tag(self):
        articles = G(Article, n=3, deleted_at=None)
        for a in articles:
            a.set_tag('some-tag')
        # It should be possible to list the articles using the tag's slug
        url = reverse('articles_list_by_tag', kwargs={'tag': 'some-tag'})
        response = self.app.get(url)
        self.assertTrue(response.html.select('ul.article-list'))
        self.assertTitlesEqual(response, articles, 'article-list')

    @skip('WIP articles are no longer in a separate list')
    def test_tag_pages_show_wip_articles_in_a_separate_list(self):
        t = G(Tag, title='some-tag')
        articles = G(Article, n=3, tags=[t], deleted_at=None)
        wip_articles = G(Article, n=3, tags=[t], deleted_at=None)
        # In this case, we really want the articles to be clearly defined as WIP, so:
        for a in wip_articles:
            a.is_wip = True
        url = reverse('articles_list_by_tag', kwargs={'tag': 'some-tag'})
        response = self.app.get(url)
        self.assertTrue(response.html.select('ul.work-in-progress'))
        self.assertTitlesEqual(response, wip_articles, 'work-in-progress')
        # It wouldn't make sense to have the same items in the regular article list, which should show only the others
        self.assertTitlesEqual(response, articles, 'article-list')

    def test_tag_page_defaults_to_showing_hot_articles(self):
        t = G(Tag, title='some-tag')
        articles = G(Article, n=3, tags=[t], deleted_at=None)
        # we just need to define one article as hot to verify that the sort order is respected
        articles[1].title = 'Hot article'
        articles[1].save()
        articles[1].receive_kudos()
        articles[1].receive_kudos(session_id='different_session_id')  # At the moment we need at least two kudos
        url = reverse('articles_list_by_tag', kwargs={'tag': 'some-tag'})
        response = self.app.get(url)
        self.assertEqual(response.html.select('ul.article-list li h4 a')[0].string, articles[1].title)

    @skip("Related tags are no longer shown in bulk in view")
    def test_tag_page_shows_related_tags(self):
        # There is no written definition of "related" tags, so I'm gonna use
        # "all the other tags referenced by the items in this query"
        t1, t2, t3 = G(Tag, title='first-tag'), G(Tag, title='second-tag'), G(Tag, title='third-tag')
        G(Tag, title='unused-tag')
        articles = G(Article, n=5, tags=[t1], deleted_at=None)
        articles[0].set_tag(t2)
        articles[1].set_tag(t2)
        articles[1].set_tag(t3)
        articles[2].set_tag(t3)
        url = reverse('articles_list_by_tag', kwargs={'tag': 'first-tag'})
        # We expect there to be a list
        response = self.app.get(url)
        self.assertTrue(response.html.select('ul.related-tags'))
        self.assertItemsEqual([t1.title, t2.title, t3.title],  # What about the current one?
                              [li.string for li in response.html.select('ul.related-tags li a.title')])

        # There should be two types of links in the list; the one with the title should lead to the referenced tag page
        # while the one with a plus sign should work as a drilldown (ie. AND together the current and the clicked tags)
        response = response.click('third-tag')
        # The response should now include only two articles (1 & 2)
        self.assertTitlesEqual(response, articles[1:3], 'article-list')

        # Now, clicking on the plus sign with any certainty would be tricky so I'm going to take a shortcut and add
        # an id to the A elements (since they're going to be unique anyway, we expect)
        response = response.click(linkid='drilldown-second-tag')
        # Now, the result should be the only article with both t2 and t3, that is articles[1]
        self.assertTitlesEqual(response, [articles[1]], 'article-list')

    def test_tag_page_supports_rss(self):
        t = G(Tag, title='sample-tag')
        url = reverse('articles_list_by_tag', kwargs={'tag': t.title})
        response = self.app.get(url)
        feed_link = response.html.find('link', attrs={'rel': 'alternate'})
        self.assertTrue(feed_link)
        response = self.app.get(feed_link['href'], status=200)
        self.assertEqual(response.content_type, 'application/rss+xml')
        # Checks on the channel elements
        channel = response.xml.find('./channel')
        self.assertEqual(channel.find('title').text, 'Recent pages in ' + t.title)
        self.assertEqual(channel.find('description').text, 'New articles from Devcharm')
        self.assertEqual(urlparse(channel.find('link').text).path, reverse('articles_feed_by_tag', args=(t.title, )))

        author = G(get_user_model())
        author.author_profile.display_name = 'the_authors_name'
        author.author_profile.save()
        self.assertEqual(author.author_profile.display_name, 'the_authors_name')
        # If we try with an actual item, now, we can check that too
        # Unpublished, so it should not show up
        a = G(Article, tags=[t], title='the title', punchline='the punchline', published_at=None, deleted_at=None,
              author=author)
        response = self.app.get(feed_link['href'])
        self.assertIsNone(response.xml.find('./channel/item'))
        a.published_at = now()
        a.save()
        response = self.app.get(feed_link['href'])
        item = response.xml.find('./channel/item')
        self.assertIsNotNone(item)
        # Some checks on the items
        host = '{}:{}'.format(response.request.host_url, response.request.host_port)
        self.assertEqual(item.find('link').text, host + a.get_absolute_url())
        self.assertTrue(item.find('pubDate').text)  # We're gonna trust them on this
        # self.assertTrue(item.find('updatedDate').text)  # This doesn't seem to be actually present in the pre_v1 feed
        self.assertEqual(item.find('title').text, a.title)
        self.assertEqual(item.find('description').text, a.punchline)
        self.assertEqual(item.find('author').text, a.author.author_profile.display_name)
        self.assertEqual(item.find('authorLink').text, host + a.author.author_profile.get_absolute_url())

        # Since, apparently, dealing with prefixes is a major PITA, it makes sense to simply check for the strings
        self.assertIn('{http://purl.org/dc/elements/1.1/}creator', [i.tag for i in item._children])

        # If we add another article with a different tag, it should not show up
        G(Article, is_published=True)
        response = self.app.get(feed_link['href'])
        self.assertEqual(len(response.xml.findall('./channel/item')), 1)

    @skip("Tags cannot currently be selected in the form")
    def test_tag_page_allows_users_to_create_new_article_with_current_tag(self):
        t = G(Tag, title='sample-tag')
        url = reverse('articles_list_by_tag', kwargs={'tag': t.title})
        response = self.app.get(url, user="someuser")
        response = response.click('write a stub')
        # The interface for the editor is not yet in place, so we'll just make sure that the form's tags has the
        # correct value
        self.assertEqual(response.form['tags'].value, [str(t.pk)])


class TestArticleDetailPageContent(WebTest):
    def test_article_detail_page_should_include_article_content(self):
        t = G(Tag, title='sample-tag')
        article = G(Article, tags=[t], title='The Title', punchline='The Punchline', description='The Description',
                    rendered_html='some <a>rendered</a> html', deleted_at=None)
        url = reverse('articles_article_detail', args=(article.pk, ))
        response = self.app.get(url)
        # Of course, we expect there to be the actual content, so:
        self.assertEqual(response.html.select('article header .title')[0].string, article.title)
        self.assertEqual(response.html.select('article header .punchline')[0].string,
                         article.punchline)
        self.assertInHTML(article.description,
                          response.html.select('article .article-description')[0].text)
        self.assertHTMLEqual(str(response.html.select('article .article-content')[0]),
                             '<div class="article-content">{}</div>'.format(article.rendered_html))

    @skip('The algorithm for determining tags related to those of current article has not yet been specified')
    def test_article_detail_page_shows_related_tags(self):
        t1, t2, t3 = G(Tag, n=3)
        article = G(Article, tags=[t1])
        url = reverse('articles_article_detail', args=(article.pk, ))
        self.app.get(url)
        self.fail('The algorithm for determining tags related to those of current article has not yet been specified')
        # self.assertTrue(response.html.select('ul.related-tags'))

    def test_article_detail_page_shows_kudos_received(self):
        article = G(Article, deleted_at=None)
        url = reverse('articles_article_detail', args=(article.pk, ))
        article.receive_kudos()
        article.receive_kudos(session_id='differentsessionid')
        response = self.app.get(url)
        self.assertEqual(response.html.select('.article-actions .kudos-count')[0].string, '2')

    def test_article_detail_page_shows_meta_content(self):
        from django.template.defaultfilters import date
        article = G(Article, received_kudos_count=5, views_count=10, revisions_count=50,
                    comments_count=100, deleted_at=None)
        url = reverse('articles_article_detail', args=(article.pk, ))
        response = self.app.get(url)
        self.assertEqual(response.html.select('.article-details span.kudos-count')[0].string,
                         str(article.received_kudos_count))
        # The view count remains the same, because the in-memory instance does not get updated, only the one in the DB
        self.assertEqual(response.html.select('.article-details span.views-count')[0].string,
                         str(article.views_count))

        # self.assertEqual(response.html.select('.article-details span.editors-count')[0].string,
        #                  str(article.editors_count))
        self.assertEqual(response.html.select('.article-details .revisions-count')[0].string,
                         str(article.revisions_count))
        self.assertEqual(response.html.select('.article-details span.last-update')[0].string,
                         date(article.updated_at, 'j M Y'))
        # self.assertEqual(response.html.select('.article-details span.comments-count')[0].string,
        #                  str(article.comments_count))

    def test_article_detail_page_allows_viewing_source(self):
        sample_content = '# Title of\n\nWith intro\n\n\And this is the body.'
        article = G(Article, raw_content=sample_content, deleted_at=None)
        # Since I'm not clear about where this should be linked from, I'm introducing a method on the object
        response = self.app.get(article.get_source_url())
        self.assertEqual(response.content_type, 'text/plain')
        self.assertEqual(response.body, sample_content)  # Nothing more, nothing less.


class TestArticleRevisionsPage(WebTest):
    @skip('Article revision list is not currently enabled')
    def test_articles_have_a_revision_history(self):
        u = G(get_user_model())
        article = G(Article, deleted_at=None)
        url = reverse('articles_article_edit', args=(article.pk, ))
        # The basic requirement is that any modifications save a new version
        response = self.app.get(url, user=u.username)
        response.form['raw_content'] = '# This is a new title\n\n\nThis content has been edited'
        response = self.app.get(response.form.submit().json['url'])
        # In the resulting page we expect to have a link to a revision history
        response = response.click(href=reverse('articles_article_revision_list', args=(article.pk, )))
        self.assertTrue(response.html.select('ul.revision-history'))
        # There should be two revisions now, with the most recent on top
        self.assertEqual(len(response.html.select('ul.revision-history li span.title')), 2)
        self.assertIn('This is a new title', response.html.select('ul.revision-history li span.title')[0])

    def test_a_specific_revision_for_an_article_can_be_retrieved(self):
        u = G(get_user_model())
        article = G(Article, raw_content='# This is the old title\n\nThis is the original description\n\n## content',
                    title='This is the old title', rendered_html='', deleted_at=None)
        url = reverse('articles_article_edit', args=(article.pk, ))
        response = self.app.get(url, user=u.username)
        response.form['raw_content'] = '# This is a new title\n\nThis description has been edited'
        response.form.submit()
        response = self.app.get(reverse('articles_article_revision_list', args=(article.pk, )))
        # Now we should be able to click on the title of the old article to see its full contents
        response = response.click(r'view revision', index=1)
        # The result should be an ArticleDetail view, with the "old" information
        self.assertEqual(response.html.select('article header .title')[0].string,
                         'This is the old title')
        self.assertInHTML('This is the original description',
                          response.html.select('article .article-description')[0].text)

    def test_diff_between_revisions_can_be_retrieved(self):
        article = G(Article, raw_content='# This is the old title\n\nThis is the description with removed content',
                    deleted_at=None)
        article.raw_content = '# This is the old title\n\nThis is the description\n\nThis is the added content'
        article.save()
        url = reverse('articles_article_revision_list', args=(article.pk, ))
        response = self.app.get(url)
        response = response.click('view diff')  # There is only one revision, so we don't have to check the index
        # This page must use a completely different template - we'll check that in the unit test
        self.assertTrue(response.html.select('table.diff'))
        self.assertTrue(response.html.select('table.diff tr td.diff--old'))
        # Line 3 has removed content so we expect there to be a <del>
        self.assertTrue(response.html.find_all('td', class_='diff--old')[2].find('del'))
        # Line 5 has added content so there should be an <ins>
        self.assertTrue(response.html.find_all('td', class_='diff--new')[4].find('ins'))

    def test_revisions_page_supports_rss(self):
        article = G(Article, raw_content='# This is the old title\n\nThis is the description with removed content',
                    deleted_at=None)
        article.raw_content = '# This is the old title\n\nThis is the description\n\nThis is the added content'
        article.save()
        url = reverse('articles_article_revision_list', args=(article.pk, ))
        response = self.app.get(url)
        feed_link = response.html.find('link', attrs={'rel': 'alternate'})
        self.assertTrue(feed_link)
        response = self.app.get(feed_link['href'], status=200)
        self.assertEqual(response.content_type, 'application/rss+xml')


class TestArticleDetailPageInteraction(WebTest):
    @skip("Tags cannot currently be selected in the form")
    def test_article_detail_page_allows_user_to_create_new_list_based_on_tag(self):
        # The main idea here is that we should leverage the tag_type to decide which tag to use
        useless_tag, useful_tag = G(Tag, title='wip', tag_type='status'), G(Tag, title='Django', tag_type='technology')
        article = G(Article, tags=[useful_tag, useless_tag], deleted_at=None)
        url = reverse('articles_article_detail', args=(article.pk, ))
        response = self.app.get(url, user="someuser")
        response = response.click('Know about {}\? Make a list!'.format(useful_tag.title))
        # It should be enough to confirm that the tag has been preselected
        self.assertEqual(response.form['tags'].value, [str(useful_tag.pk)])

    def test_article_detail_page_allows_user_to_give_kudos(self):
        article = G(Article, deleted_at=None)
        url = reverse('articles_article_detail', args=(article.pk, ))
        response = self.app.get(url)
        kudos_form = response.forms['kudos-form-{}'.format(article.pk)]
        kudos_form.submit().maybe_follow()
        self.assertEqual(Article.objects.get(pk=article.pk).received_kudos_count, 1)

    def test_article_detail_page_allows_user_to_edit_if_editable(self):
        article = G(Article, raw_content='Some raw content', deleted_at=None, is_wiki=True)
        url = reverse('articles_article_detail', args=(article.pk, ))
        response = self.app.get(url, user='someuser')
        response = response.click('Edit article')
        self.assertEqual(response.form['raw_content'].value, article.raw_content)
        # the easiest check is for wip status; if we remove it, the article should be uneditable and thus the link
        # should disappear
        article.is_wiki = False
        article.save()
        response = self.app.get(url)
        self.assertFalse(response.html.find('a', text='Edit this'))


class TestProfilePageContent(DevcharmContentTest):
    @skip('Currently not available')
    def test_page_suggests_high_kudos_wip_articles(self):
        low_kudos = G(Article, n=5, deleted_at=None)
        high_kudos = G(Article, received_kudos_count=10, deleted_at=None,
                       n=settings.PROFILE_PAGE_NUM_SUGGESTED_WIP_ARTICLES)
        # The fundamental expectation is that no low kudos article will be shown in the profile page, while the high
        # kudos one will. Also note that, since the count has not be agreed upon, it makes sense to have it in settings,
        # and that only WIP + wiki lists should appear.
        for a in high_kudos + low_kudos:
            a.is_wip = True
        u = G(get_user_model())
        url = reverse('profiles_profile')  # We're looking at our own private profile
        response = self.app.get(url, user=u.username)
        self.assertTrue(response.html.select('ul.suggested-wip-articles'))
        self.assertTitlesEqual(response, high_kudos, 'suggested-wip-articles')
        # Since they're WIP, we also expect there to be a certain number of "Edit this" links
        self.assertEqual(len(response.html.find_all('a', text='Edit this')),
                         settings.PROFILE_PAGE_NUM_SUGGESTED_WIP_ARTICLES)

    def test_page_includes_recently_kudoed_articles(self):
        u = G(get_user_model())
        G(Article, n=5, deleted_at=None)  # These articles should not appear, we use them only as control
        kudoed = G(Article, n=5, deleted_at=None)
        for a in kudoed:
            a.receive_kudos(user=u)
        url = reverse('profiles_profile')  # We're looking at our own private profile
        response = self.app.get(url, user=u.username)
        self.assertTrue(response.html.select('ul.recent-kudos'))
        self.assertTitlesEqual(response, kudoed, 'recent-kudos')

    def test_page_includes_user_score_and_motivation(self):
        u = G(get_user_model())
        # Ideally we'd want an example for every possible scenario; at the moment, it should be enough to
        # test the most easily appliable circumstance (receiving kudos as author)
        a = G(Article, author=u)
        a.receive_kudos(session_id='session1')
        a.receive_kudos(session_id='session2')
        url = reverse('profiles_profile')  # We're looking at our own private profile
        response = self.app.get(url, user=u.username)
        self.assertTrue(response.html.select('div.devcharm-score'))
        self.assertEqual(response.html.select('div.devcharm-score .value')[0].string,
                         str(get_user_model().objects.get(pk=u.pk).author_profile.score))

        # Score history has been currently removed

        # self.assertTrue(response.html.select('ul.score-history'))
        # self.assertItemsEqual(['Received kudos for article {}'.format(a.pk)] * 2,
        #                       [li.string for li in response.html.select('ul.score-history li span.description')])
        # self.assertItemsEqual([str(settings.ACTIVITY_POINTS['receiving_kudos_as_author'])] * 2,
        #                       [li.string for li in response.html.select('ul.score-history li span.points')])
        # # While I believe it would make sense to also test for the formatting of the transaction's
        # # timestamp, we have not defined a format, so I'm leaving this out (the data is there, so we can consider
        # # it a 3rd-party test, which is not really necessary).
        # self.assertEqual(len(response.html.select('ul.score-history li span.timestamp')), 2)


class TestProfileEditing(WebTest):
    def test_users_can_edit_their_own_profile(self):
        u = G(get_user_model())
        u.author_profile.bio = 'Initial bio'
        u.author_profile.save()
        url = reverse('profiles_edit_own_profile')  # There should be no reason to edit other people's profiles.
        self.app.reset()
        self.app.get(url, status=404)  # When viewed without being logged in, it should be 404
        response = self.app.get(url, user=u.username)  # When logged in, we should have the form etc.
        # The form should not have sensitive fields like score, user & can_publish
        self.assertNotIn('score', response.form.fields)
        self.assertNotIn('user_id', response.form.fields)
        self.assertNotIn('can_publish', response.form.fields)
        # The initial values should be those of u.author_profile
        self.assertEqual(u.author_profile.bio, response.form['bio'].value)
        response.form['display_name'] = 'Shiny new name'
        response.form['bio'] = 'Matching bio'
        response = response.form.submit().follow()
        # We should now be at the user's profile page with updated info
        updated_profile = response.context['author_profile']
        self.assertEqual(updated_profile.display_name, 'Shiny new name')
        self.assertEqual(updated_profile.bio, 'Matching bio')


class TestRESTlikeInterface(WebTest):
    def test_articles_can_be_created_and_updated_restlike(self):
        # First, we want to create a new article by POSTing outside a form (and without CSRF checks)
        u = G(get_user_model(), username="test_user")
        data = {
            'raw_content': '# Title REST\n>Then punchline\n\nAnd intro\n\n\- Finally the body.'
        }
        response = self.app.post(reverse('articles_article_rest_save'), params=data, user=u.username)
        self.assertIn('pk', response.json)  # The output should include the PK of the newly created Article.
        article_pk = response.json['pk']
        new_url = response.json['url']
        response = self.app.get(new_url, user=u.username)
        self.assertEqual(response.html.select('article header h1.title')[0].string, 'Title REST')

        # Editing should be simple
        data['raw_content'] = '# Title REST\n>Then different punchline\n\nAnd intro\n\n\- Finally the body.'
        put_url = reverse('articles_article_rest_save', args=(article_pk, ))
        response = self.app.post(put_url, params=data)  # PUT-like
        response = self.app.get(response.json['url'], user=u.username)
        self.assertEqual(response.html.select('article header .punchline')[0].string,
                         'Then different punchline')

    def test_articles_can_be_published_restlike(self):
        article = G(Article, published_at=None, deleted_at=None)
        self.app.get(article.get_absolute_url(), status=404)  # Sanity check
        response = self.app.post(reverse('articles_article_rest_publish', args=(article.pk,)),
                                 user=article.author.username)
        # As usual, we would like to get some JSON data back
        self.assertIn('pk', response.json)
        # Let's check that the article has been properly updated
        self.app.get(response.json['url'])
        # On the other hand, if it has already been published we don't want to change the timestamp
        article.published_at = now() - timedelta(7)
        old_timestamp = article.published_at
        article.save()
        self.app.post(reverse('articles_article_rest_publish', args=(article.pk,)))
        self.assertEqual(Article.objects.get(pk=article.pk).published_at, old_timestamp)

    def test_articles_can_received_kudos_restlike(self):
        article = G(Article)
        response = self.app.post(reverse('articles_article_rest_kudos', args=(article.pk,)))
        # In this case, we expect the response to be simply the current kudos count
        self.assertEqual(response.body, '1')

    def test_articles_can_be_deleted_restlike(self):
        u, u2 = G(get_user_model(), n=2)
        article = G(Article, author=u, deleted_at=None)  # Published
        # sanity check
        response = self.app.get(article.get_absolute_url())
        self.assertIsNone(response.context['article'].deleted_at)
        # Anon users will receive a 403 Forbidden...
        url = reverse('articles_article_rest_delete', args=(article.pk,))
        self.app.post(url, status=403)
        # ...while other users will receive a 404
        self.app.post(url, user=u2.username, status=404)
        # The author will receive the proper response (pk + url)
        response = self.app.post(url, user=u.username)
        self.assertEqual(response.json['pk'], article.pk)
        # If we follow the URL we should find a deleted article (which means 404)
        self.app.get(response.json['url'], user=u.username, status=404)

        # Admins should be able to do the same, of course
        admin = G(get_user_model(), is_superuser=True)
        self.app.post(url, user=admin.username, status=200)

    def test_views_can_be_added_to_articles_restlike(self):
        article = G(Article)
        admin = G(get_user_model(), is_superuser=True)
        # Please note that we have to use a superuser here
        response = self.app.post(reverse('articles_article_rest_add_view', args=(article.pk,)), user=admin.username)
        # In this case, we expect the response to be simply the current views count
        self.assertEqual(response.body, '1')


class TestURLs(WebTest):
    def test_old_urls_redirect_to_current_content(self):
        a = G(Article, title='sample slug', deleted_at=None, slug="sample-slug")
        # Since we should not be referincing these URLs in templates, we're going to check using actual strings.
        url = '/pages/{}'.format(a.pk)
        response = self.app.get(url)
        # These redirects should be permanent
        self.assertRedirects(response, reverse('articles_article_detail', args=(a.pk, )), status_code=301)
        # Also required is id+slug
        url = '/pages/{}-sample-slug'.format(a.pk)
        response = self.app.get(url)
        self.assertRedirects(response, reverse('articles_article_detail', kwargs={'pk': a.pk, 'slug': a.slug}),
                             status_code=301)
        # History too:
        url = '/pages/{}-sample-slug/history'.format(a.pk)
        response = self.app.get(url)
        self.assertRedirects(response, reverse('articles_article_revision_list', kwargs={'pk': a.pk, 'slug': a.slug}),
                             status_code=301)

    def test_sitemaps_are_present_and_active(self):
        articles = G(Article, deleted_at=None, published_at=now(), kudos_received=10, n=3)
        tags = G(Tag, n=3, title="sample-tag")
        url = reverse('sitemap')
        response = self.app.get(url)
        self.assertTrue(response.xml.findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url'))  # Actual sitemap
        self.assertContains(response, articles[0].get_absolute_url())
        self.assertContains(response, reverse('articles_list_by_tag', args=(tags[0].title, )))


class TestTags(WebTest):
    def test_tags_autogenerate_slugs(self):
        t = Tag(title='title with spaces')
        t.save()
        self.assertEqual(t.title, 'title-with-spaces')
        # saving the tag twice should not change its title
        t.save()
        self.assertEqual(t.title, 'title-with-spaces')
        # A second tag with the same title should return a different slug
        t2 = Tag(title='title with spaces')
        t2.save()
        self.assertEqual(t2.title, 'title-with-spaces-1')
        # Since we're using a different char to avoid collisions, we can also save tags with numbers
        G(Tag, title='Tag 4')
        G(Tag, title='Tag', n=4)
        G(Tag, title='Tag 7')
        G(Tag, title='Tag', n=4)
        self.assertEqual(Tag.objects.latest('pk').title, 'tag-10')

    def test_titles_substring_do_not_collide(self):
        G(Tag, title='django')
        t = Tag(title='go')
        t.save()
        self.assertEqual(t.title, 'go')
