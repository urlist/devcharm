# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.unittest.case import skip
from django_dynamic_fixture import G
from django_webtest import WebTest
from tags.models import Tag
from tags.tests.test_models import BasicModel


class TestTaggingViews(WebTest):
    csrf_checks = False

    @skip('Not implemented yet')
    def test_view_a_list_of_tags_for_an_object(self):
        o = G(BasicModel)
        url = reverse('tags_tags_for_object', kwargs={'object_id': o.pk,
                                                      'content_type': ContentType.objects.get_for_model(o).pk})
        # now the view should return an empty list
        response = self.app.get(url, status=200)  # 200 - the list should not require login or permissions
        self.assertFalse(response.context['tag_list'])
        # Adding a tag to the object should return an item in the list
        o.set_tag('tag')
        response = self.app.get(url, status=200)  # 200 - the list should not require login or permissions
        self.assertEqual(len(response.context['tag_list']), 1)

    @skip('Not implemented yet')
    def test_tags_can_be_assigned_to_objects(self):
        o = G(BasicModel)
        # Initially, I wanted to use the model name but I'm afraid it might lead to unwanted consequences, so for now
        # it's gonna use the contenttype.pk
        url = reverse('tags_tag_object', kwargs={'object_id': o.pk,
                                                 'content_type': ContentType.objects.get_for_model(o).pk})
        response = self.app.post(url)
        self.assertEqual(response.status_code, 302)  # Redirect - we want the POST action to be allowed only on login

        user = G(get_user_model())
        response = self.app.post(url, user=user.username)
        self.assertFormError(response, 'form', 'title', 'This field is required.')  # Bad Request - missing tag title

        # Let's try with the correct stuff in
        response = self.app.post(url, user=user.username, params={'title': 'some tag title'}).follow()
        # we expect a redirect to the tagged object's tag list
        self.assertTrue(response.context['tag_list'])
        self.assertTrue(o.has_tag('some tag title'))

    @skip('Not implemented yet')
    def test_tags_can_be_listed(self):
        url = reverse('tags_list')
        response = self.app.get(url, status=200)
        self.assertFalse(response.context['tag_list'])
        G(Tag, n=5)
        response = self.app.get(url, status=200)
        self.assertEqual(len(response.context['tag_list']), 5)