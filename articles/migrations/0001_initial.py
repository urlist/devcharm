# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):
    depends_on = (
        ("tags", "0001_initial"),
    )

    def forwards(self, orm):
        # Adding model 'Article'
        db.create_table(u'articles_article', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=255)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('punchline', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('rendered_html', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('raw_content', self.gf('django.db.models.fields.TextField')()),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('published_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_wiki', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('hide', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('submitted_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('deleted_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('views_count', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('received_kudos_count', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('editors_count', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('revisions_count', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('comments_count', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
        ))
        db.send_create_signal(u'articles', ['Article'])

        # Adding M2M table for field tags on 'Article'
        m2m_table_name = db.shorten_name(u'articles_article_tags')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('article', models.ForeignKey(orm[u'articles.article'], null=False)),
            ('tag', models.ForeignKey(orm[u'tags.tag'], null=False))
        ))
        db.create_unique(m2m_table_name, ['article_id', 'tag_id'])

        # Adding model 'Kudos'
        db.create_table(u'articles_kudos', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('article', self.gf('django.db.models.fields.related.ForeignKey')(related_name='kudos_received', to=orm['articles.Article'])),
            ('session_id', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='kudos_given', null=True, to=orm['auth.User'])),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'articles', ['Kudos'])

        # Adding unique constraint on 'Kudos', fields ['article', 'session_id']
        db.create_unique(u'articles_kudos', ['article_id', 'session_id'])

        # Adding unique constraint on 'Kudos', fields ['article', 'user']
        db.create_unique(u'articles_kudos', ['article_id', 'user_id'])

        # Adding model 'ArticleView'
        db.create_table(u'articles_articleview', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('article', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['articles.Article'])),
            ('session_id', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='viewed_pages', null=True, to=orm['auth.User'])),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'articles', ['ArticleView'])

        # Adding model 'ArticleGroup'
        db.create_table(u'articles_articlegroup', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('publish_start', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('target_block', self.gf('django.db.models.fields.CharField')(default='editors_picks', max_length=255)),
        ))
        db.send_create_signal(u'articles', ['ArticleGroup'])

        # Adding M2M table for field articles on 'ArticleGroup'
        m2m_table_name = db.shorten_name(u'articles_articlegroup_articles')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('articlegroup', models.ForeignKey(orm[u'articles.articlegroup'], null=False)),
            ('article', models.ForeignKey(orm[u'articles.article'], null=False))
        ))
        db.create_unique(m2m_table_name, ['articlegroup_id', 'article_id'])

        # Adding model 'Revision'
        db.create_table(u'articles_revision', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('article', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['articles.Article'])),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('punchline', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('raw_content', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'articles', ['Revision'])


    def backwards(self, orm):
        # Removing unique constraint on 'Kudos', fields ['article', 'user']
        db.delete_unique(u'articles_kudos', ['article_id', 'user_id'])

        # Removing unique constraint on 'Kudos', fields ['article', 'session_id']
        db.delete_unique(u'articles_kudos', ['article_id', 'session_id'])

        # Deleting model 'Article'
        db.delete_table(u'articles_article')

        # Removing M2M table for field tags on 'Article'
        db.delete_table(db.shorten_name(u'articles_article_tags'))

        # Deleting model 'Kudos'
        db.delete_table(u'articles_kudos')

        # Deleting model 'ArticleView'
        db.delete_table(u'articles_articleview')

        # Deleting model 'ArticleGroup'
        db.delete_table(u'articles_articlegroup')

        # Removing M2M table for field articles on 'ArticleGroup'
        db.delete_table(db.shorten_name(u'articles_articlegroup_articles'))

        # Deleting model 'Revision'
        db.delete_table(u'articles_revision')


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
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'tagged_article_set'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['tags.Tag']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'views_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        u'articles.articlegroup': {
            'Meta': {'object_name': 'ArticleGroup'},
            'articles': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['articles.Article']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'publish_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'target_block': ('django.db.models.fields.CharField', [], {'default': "'editors_picks'", 'max_length': '255'})
        },
        u'articles.articleview': {
            'Meta': {'object_name': 'ArticleView'},
            'article': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['articles.Article']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session_id': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'viewed_pages'", 'null': 'True', 'to': u"orm['auth.User']"})
        },
        u'articles.kudos': {
            'Meta': {'unique_together': "[('article', 'session_id'), ('article', 'user')]", 'object_name': 'Kudos'},
            'article': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'kudos_received'", 'to': u"orm['articles.Article']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session_id': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'kudos_given'", 'null': 'True', 'to': u"orm['auth.User']"})
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
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
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
        }
    }

    complete_apps = ['articles']