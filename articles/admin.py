from django.contrib import admin
from django import forms

# Register your models here.
from articles.models import ArticleGroup, Article


class OnlyPublishedFilter(admin.SimpleListFilter):
    title = 'status'

    parameter_name = 'is_published'

    def lookups(self, request, model_admin):
        return (('1', 'published'),
                ('0', 'unpublished'))

    def value(self):
        return super(OnlyPublishedFilter, self).value() == '0'

    def queryset(self, request, queryset):
        return queryset.filter(published_at__isnull=self.value())


class ArticleAdmin(admin.ModelAdmin):
    model = Article
    list_display = ['title', 'slug', 'author', 'published_at',
                    'is_wiki', 'views_count', 'received_kudos_count',
                    'links_count', 'keywords']
    list_editable = ('published_at', 'is_wiki')
    list_filter = ('is_wiki', 'tags', OnlyPublishedFilter)
    search_fields = ['title',]
    filter_horizontal = ['tags',]


class ArticleGroupAdmin(admin.ModelAdmin):
    model = ArticleGroup
    filter_horizontal = ('articles', )


admin.site.register(Article, ArticleAdmin)
admin.site.register(ArticleGroup, ArticleGroupAdmin)
