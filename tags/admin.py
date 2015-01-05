from django.contrib import admin
from tags.models import Tag


class TagAdmin(admin.ModelAdmin):
    model = Tag
    list_display = ('title', 'verbose_title', 'tag_type')
    list_editable = ('verbose_title', 'tag_type')


admin.site.register(Tag, TagAdmin)
