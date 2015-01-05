# -*- coding: utf-8 -*-
from django.db.utils import IntegrityError, ProgrammingError
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models, connection
from articles.models import Article


class Migration(DataMigration):
    def get_full_raw_content(self, page):
        return u'# {}\n\n> {}\n\n{}\n\n{}'.format(page.title, page.punchline, page.description, page.raw_content)

    def forwards(self, orm):
        if not 'pages_page' in connection.introspection.table_names():
            # The table does not exists, which means that we're running on a fresh installation, so we can skip
            # the whole migration
            return

        for page in orm['pages.page'].objects.exclude(author__user_id=308):
            defaults = {'created_at': page.created_at,
                        'deleted_at': page.deleted_at,
                        'hide': page.hide,
                        'is_wiki': page.is_wiki,
                        'published_at': page.published_at,
                        'raw_content': self.get_full_raw_content(page),
                        'slug': page.slug.lower(),
                        'submitted_at': page.submitted_at,
                        'title': page.title,
                        'updated_at': page.updated_at,
                        'views_count': page.views,
                        'received_kudos_count': page.karma,
                        'revisions_count': page.pagerevision_set.count(),
                        # Special treatment required
                        'author_id': page.author.user_id, }
            rendered_content = Article.process_raw_content(defaults['raw_content'])
            defaults['rendered_html'] = rendered_content['rendered_html']
            defaults['description'] = rendered_content['description']
            defaults['punchline'] = rendered_content['punchline']
            a, created = orm['articles.article'].objects.get_or_create(pk=page.pk, defaults=defaults)

            a.tags.clear()
            for tag in page.tags.all():
                apply_tag, tag_created = orm['tags.tag'].objects.get_or_create(pk=tag.pk,
                                                                               defaults={'title': tag.name})
                a.tags.add(apply_tag)

            a.revision_set.all().delete()
            for rev in page.pagerevision_set.all():
                rev_values = {
                    'author': rev.author.user,
                    'created_at': rev.created_at,
                    'raw_content': self.get_full_raw_content(rev),
                    'title': rev.title,
                }
                rendered_content = Article.process_raw_content(defaults['raw_content'])
                rev_values['description'] = rendered_content['description']
                rev_values['punchline'] = rendered_content['punchline']
                a.revision_set.create(pk=rev.pk, **rev_values)

            a.kudos_received.all().delete()
            for kudos in page.pagekarma_set.all():
                kudos_values = {
                    'user': kudos.user,
                    'session_id': kudos.session_id,
                    'timestamp': kudos.timestamp,
                }
                a.kudos_received.create(**kudos_values)

            a.articleview_set.all().delete()
            for v in page.pageview_set.all():
                view_values = {
                    'user': v.user,
                    'session_id': v.session_id,
                    'timestamp': v.timestamp,
                }
                a.articleview_set.create(**view_values)

    def backwards(self, orm):
        pass

    models = {
        u'articles.article': {
            'Meta': {'object_name': 'Article'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'comments_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'editors_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'hide': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_wiki': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'published_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'punchline': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'raw_content': ('django.db.models.fields.TextField', [], {}),
            'received_kudos_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'rendered_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'revisions_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'submitted_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [],
                     {'blank': 'True', 'related_name': "'tagged_article_set'", 'null': 'True', 'symmetrical': 'False',
                      'to': u"orm['tags.Tag']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'views_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        u'articles.articlegroup': {
            'Meta': {'object_name': 'ArticleGroup'},
            'articles': ('django.db.models.fields.related.ManyToManyField', [],
                         {'symmetrical': 'False', 'to': u"orm['articles.Article']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'publish_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'target_block': (
                'django.db.models.fields.CharField', [], {'default': "'editors_picks'", 'max_length': '255'})
        },
        u'articles.articleview': {
            'Meta': {'object_name': 'ArticleView'},
            'article': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['articles.Article']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session_id': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [],
                     {'blank': 'True', 'related_name': "'viewed_pages'", 'null': 'True', 'to': u"orm['auth.User']"})
        },
        u'articles.kudos': {
            'Meta': {'unique_together': "[('article', 'session_id'), ('article', 'user')]", 'object_name': 'Kudos'},
            'article': ('django.db.models.fields.related.ForeignKey', [],
                        {'related_name': "'kudos_received'", 'to': u"orm['articles.Article']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session_id': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [],
                     {'blank': 'True', 'related_name': "'kudos_given'", 'null': 'True', 'to': u"orm['auth.User']"})
        },
        u'articles.revision': {
            'Meta': {'ordering': "['-pk']", 'object_name': 'Revision'},
            'article': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['articles.Article']"}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'punchline': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'raw_content': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [],
                            {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')",
                     'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': (
                'django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [],
                       {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True',
                        'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [],
                                 {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True',
                                  'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)",
                     'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'tags.tag': {
            'Meta': {'object_name': 'Tag'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'tag_type': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'title': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        u'pages.page': {
            'Meta': {'object_name': 'Page'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pages.PageAuthor']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'hide': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_wiki': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'karma': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'published_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'punchline': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'raw_content': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'submitted_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [],
                     {'symmetrical': 'False', 'to': u"orm['pages.PageTag']", 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'views': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        u'pages.pageauthor': {
            'Meta': {'object_name': 'PageAuthor'},
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'can_publish': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'karma': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'user': (
            'django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'}),
            'website': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'})
        },
        u'pages.pagetag': {
            'Meta': {'object_name': 'PageTag'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        u'pages.pageview': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'PageView'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'page': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pages.Page']"}),
            'session_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'})
        },
        u'pages.pagekarma': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'PageKarma'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'page': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pages.Page']"}),
            'session_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'})
        },
        u'pages.pagerevision': {
            'Meta': {'object_name': 'PageRevision'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pages.PageAuthor']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'page': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pages.Page']"}),
            'punchline': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'raw_content': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
    }

    complete_apps = ['articles']
    symmetrical = True
