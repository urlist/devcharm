# Create your views here.
# Create your views here.
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views.generic import DetailView, ListView, CreateView, View

from tags.models import Tag


# class TagDetailView(DetailView):
#     """
#     This class is used to show the comments on a tag (ie. meta). The one used to show objects with a certain tag is
#     TaggedObjectsListView
#     """
#     model = Tag
#     template_name = 'tags/tag_detail.html'
#
#
class TagListView(ListView):
    model = Tag
    template_name = 'tags/tag_list.html'


# class TaggedObjectsListView(PostableMixin, ListView):
#     template_name = 'tags/tagged_objects_list.html'  # FIXME TEMPORARY
#     paginate_by = 50
#
#     def get_queryset(self):
#         tag = get_object_or_404(Tag, slug=self.kwargs.get('slug'))
#         return tag.taggedobject_set.prefetch_related('obj')
#
#     def get_postable_initial(self):
#         return {'tags': self.kwargs.get('slug')}


class TaggedObjectLookupMixin(View):
    tagged_object = None

    def dispatch(self, request, *args, **kwargs):
        # Setting the tagged object here should allo us to use it everywhere it's useful
        model = ContentType.objects.get_for_id(self.kwargs.get('content_type')).model_class()
        self.tagged_object = get_object_or_404(model, pk=self.kwargs.get('object_id'))
        return super(TaggedObjectLookupMixin, self).dispatch(request, *args, **kwargs)


class TagAddOrCreate(TaggedObjectLookupMixin, CreateView):
    fields = ['title']
    template_name = 'tags/add_tag_form.html'

    def get_success_url(self):
        return self.tagged_object.get_tag_list_url()

    def get_queryset(self):
        return self.tagged_object.tags.all()

    def get_form_kwargs(self):
        kwargs = super(TagAddOrCreate, self).get_form_kwargs()
        data = kwargs['data'].copy()
        data['title'] = slugify(data.get('title', u''))
        kwargs['data'] = data
        return kwargs

    def form_valid(self, form):
        self.tagged_object.set_tag(form.cleaned_data['title'])
        # We're not using the super here, since we're not actually saving the Tag
        return redirect(self.get_success_url())

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        return super(TagAddOrCreate, self).post(request, *args, **kwargs)


class TagListOnObject(TaggedObjectLookupMixin, ListView):
    def get_queryset(self):
        return self.tagged_object.tags.all()