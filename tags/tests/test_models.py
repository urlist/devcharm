import datetime
from django.db import models
from django.db.models.query import QuerySet
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils.timezone import now
from django.utils.unittest.case import skip
from django_dynamic_fixture import G

from tags.models import Tag, Taggable


class TaggableMixinTest(TestCase):
    def test_taggable_adds_m2m_to_tag(self):
        m = G(BasicModel)
        t = G(Tag)
        m.tags.add(t)
        self.assertItemsEqual(m.tags.all(), [t])

    def test_tag_methods(self):
        m = G(BasicModel)
        m.set_tag('random tag title')
        self.assertTrue(m.has_tag('random tag title'))
        # You should also be able to set a tag using a Tag object
        t = G(Tag, title='different title')
        m.set_tag(t)
        self.assertTrue(m.has_tag('different title'))

    def test_setting_tag_sets_tag_updated_datetime(self):
        updated = now() - datetime.timedelta(1)
        t = G(Tag, updated=updated)
        m = G(BasicModel)
        m.set_tag(t)
        self.assertNotEqual(updated, t.updated)
        # The same should hold true when updating a tag with the title only
        t.updated = updated
        t.save()
        m.set_tag(t.title)
        self.assertNotEqual(updated, Tag.objects.get(pk=t.pk).updated)

    def test_tags_can_be_set_more_than_once_on_different_objects(self):
        o1, o2 = G(BasicModel, n=2)
        o1.set_tag('sample tag')
        o2.set_tag('sample tag')
        self.assertTrue(o2.has_tag('sample tag'))

    def test_taggable_manager_can_return_the_numerosity_of_tags_in_a_queryset(self):
        o1, o2, o3 = G(BasicModel, n=3)
        t1, t2, t3 = G(Tag, n=3)
        o1.set_tag(t1)
        o2.set_tag(t1)
        # The end result of this should be a properly sorted Tag queryset with all and only the tags referenced by the
        # objects
        qs = BasicModel.objects_as_tagged.get_tags_by_count()
        self.assertIsInstance(qs, QuerySet)
        self.assertEqual(qs.model, Tag)
        self.assertItemsEqual([t1, ], qs)
        # Adding a new tag should result in it appearing in the resulting queryset
        o3.set_tag(t2)
        qs = BasicModel.objects_as_tagged.get_tags_by_count()
        self.assertItemsEqual([t1, t2, ], qs)
        # The order should depend on the numerosity
        o1.set_tag(t3)
        o2.set_tag(t3)
        o3.set_tag(t3)
        qs = BasicModel.objects_as_tagged.get_tags_by_count()
        self.assertSequenceEqual([t3, t1, t2], qs)
        # And the numerosity should exist as a readable attribute, of course (sanity check)
        self.assertEqual(qs[0].uses_count, 3)

        # The same method should be useable also with a custom queryset
        qs = BasicModel.objects_as_tagged.get_tags_by_count(BasicModel.objects.filter(pk__in=[o1.pk, o2.pk]))
        self.assertSequenceEqual([t3, t1, ], qs)  # t2 does not appear since it's been set only on o3

        # Finally, we should be able to use a list of pks too, since that's basically what we end up looking for anyway
        qs = BasicModel.objects_as_tagged.get_tags_by_count([o1.pk, o2.pk])
        self.assertSequenceEqual([t3, t1, ], qs)


class TagModelTestCase(TestCase):
    @skip('Made obsolete by changes in save() method')
    def test_tag_title_is_unique_and_slug(self):
        t = Tag(title='a title')
        t.save()
        self.assertEqual(t.title, 'a-title')
        t2 = Tag(title='a title')
        self.assertRaises(IntegrityError, lambda: t2.save())

    def test_tags_have_types(self):
        # We expect tags to have four types: technology, field, status, category
        for t in ['technology', 'field', 'status', 'category']:
            tag = G(Tag, tag_type=t)
            self.assertEqual(tag.tag_type, t)
        # Please note that we are NOT validating the data, so it's theoretically possible to save an invalid type
        # by using the manager directly.


class BasicModel(Taggable, models.Model):
    title = models.CharField(max_length=255)
    objects = models.Manager()  # I have no idea why I need to add this explicitely, but apparently this is so.

    class Meta:
        app_label = 'tags'