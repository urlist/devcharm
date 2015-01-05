from django.conf.urls import patterns, url
from django.views.generic import TemplateView

urlpatterns = patterns(
    '',
    url(r'^manifesto$', TemplateView.as_view(template_name='docs/manifesto.html'), name='docs_manifesto'),
    url(r'^about$', TemplateView.as_view(template_name='docs/about.html'), name='docs_about'),
    url(r'^guidelines$', TemplateView.as_view(template_name='docs/guidelines.html'), name='docs_guidelines'),
    url(r'^terms$', TemplateView.as_view(template_name='docs/terms.html'), name='docs_terms'),
)

