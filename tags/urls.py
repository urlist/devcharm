from django.conf.urls import patterns, url
from tags.views import TagAddOrCreate, TagListOnObject, TagListView


urlpatterns = patterns(
    '',
    url(r'^$', TagListView.as_view(), name='tags_list'),
    # url(r'^(?P<slug>[-a-z0-9]+)/talk$', TagDetailView.as_view(), name='tags_comments'),
    # url(r'^(?P<slug>[-a-z0-9]+)/$', TaggedObjectsListView.as_view(), name='tags_objects_list'),
    url(r'^set/(?P<content_type>\d+)/(?P<object_id>\d+)/$', TagAddOrCreate.as_view(), name='tags_tag_object'),
    url(r'^list/(?P<content_type>\d+)/(?P<object_id>\d+)/$', TagListOnObject.as_view(), name='tags_tags_for_object'),
)
