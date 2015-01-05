from unittest import TestCase, skip
from django.core.urlresolvers import reverse
from django_webtest import WebTest
from styleguide import cfg


class TestStyleguide(WebTest):
    def test_styleguide_template_view_renders_correct_template(self):
        url = reverse('styleguide_view_template', args=('styleguide:test_template', ))
        response = self.app.get(url)
        self.assertTemplateUsed(response, 'styleguide/test_template.html')

    def test_styleguide_template_view_renders_correct_context(self):
        url = reverse('styleguide_view_template', args=('styleguide:test_template', ))
        response = self.app.get(url)
        self.assertIn('sample_placeholder', response.context)

    @skip('Trending tags are not used in the landing page')
    def test_styleguide_shows_expected_context_data(self):
        url = reverse('styleguide_view_articles_home')
        response = self.app.get(url)
        self.assertIn('trending_tags', response.context)



class TestCFG(TestCase):
    def test_no_extra_spaces_are_generated(self):
        grammar = cfg.parse("""
        $s -> $cats\\n$actions
        $cats -> pille | shmui
        $actions -> runs fast | eats
        """)
        g = grammar.generate('$s')
        self.assertIn(g, ['pille\nruns fast', 'shmui\nruns fast',
                          'pille\neats', 'shmui\neats'])

    def test_underscore_is_supported(self):
        grammar = cfg.parse("""
        $s -> $omg_cats\\n$actions
        $omg_cats -> pille | shmui
        $actions -> runs fast | eats
        """)
        g = grammar.generate('$s')
        self.assertIn(g, ['pille\nruns fast', 'shmui\nruns fast',
                          'pille\neats', 'shmui\neats'])

    def test_extra_chars_are_supported(self):
        grammar = cfg.parse("""
        $s -> $cats.\\n$actions
        $cats -> pille | shmui
        $actions -> runs fast! | eats!
        """)
        g = grammar.generate('$s')
        self.assertIn(g, ['pille.\nruns fast!', 'shmui.\nruns fast!',
                          'pille.\neats!', 'shmui.\neats!'])
