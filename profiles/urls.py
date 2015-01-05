from django.conf.urls import patterns, url
from profiles.views import ProfileDetailView, ProfileEditView


urlpatterns = patterns(
    '',
    url(r'^$', ProfileDetailView.as_view(), name="profiles_profile"),
    url(r'^edit/$', ProfileEditView.as_view(), name="profiles_edit_own_profile"),
    url(r'^signup-completed/$', 'profiles.views.track_signup', name="profiles_track_signup"),
    url(r'^(?P<username>\S+)/$', ProfileDetailView.as_view(), name="profiles_profile"),
)
