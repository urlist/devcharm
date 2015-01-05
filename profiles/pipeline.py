from django.shortcuts import redirect
from social.pipeline.partial import partial as partial_pipeline

from profiles.models import Author

@partial_pipeline
def complete_profile(strategy, details, user=None, is_new=False, *args, **kwargs):
    tracked = strategy.session_pop('tracked')

    if tracked or (user and not is_new):
        return

    strategy.session_set('tracked', True)
    return redirect('profiles_track_signup')

