import datetime
from random import randint

from django.db.models.signals import post_save
from django.template import VariableNode, loader
from django.views.generic import TemplateView, DetailView
from django.contrib.auth.models import User
import factory
from factory.compat import UTC
import factory.django
from factory import fuzzy
import markdown
from django.views.generic import CreateView, UpdateView, ListView, View


from articles.models import Article
from profiles.views import AuthorForm
from articles.views import ArticleListView, ArticleDetailView, ArticleCreateView
from profiles.models import Author
from styleguide import cfg


GRAMMAR = cfg.parse("""
$title -> $opening $what $detail $how

$opening -> Must have | The | Essential | Methods for | The jungle of
$what -> HTML5 | Objective-C | GO | Javascript | Scrum | Agile | CSS | Android | Test driven development
$detail -> stack order | hierarchy | training | learning | cherry picking | nipple twisting
$how -> explained | uncovered | analyzed | olympycs

$punchline -> $useless $success just by $cat_action $cat. $intro $action $what
$useless -> How to | Think about it, you can | Stop having fear, | Act now, and | You can
$success -> build successful websites | increase your growth | increase your traffic | have a low latency API | use less memory | get rid of junk | hack your community
$cat_action -> adding | removing | publishing | connecting | networking | training
$cat -> a cat | some kittens | dogs | a honey badger | a horse | several horses | dolphins
$intro -> Here is a collection of techniques | Read through those useful resources you can use | Learn how | All you need to start your journey
$action -> to learn | to improve | to escalate | to research | to grok | to study


$tag -> web | python | backend | nerdcore | productivity | css | frontend | intro | php | go | javascript | wip | frameworks | pro | web-development | chrome | gaming | html5 | django | start-with | courses | mobile | ios | testing | git | web-design | funcprog | haskell | best-of | tools | agile | management | soft-skills | tricks | fun | culture | reading | documentation | ruby | robotics | regexp | events | android | oop | kids | cms | firefoxos | scm | server | browser | console | vim | science | open-source | academics


$display_name -> $first_name $last_name
$first_name -> Pino | Guglielmo | John | Michael
$last_name -> Marino | Pinolo | Smith
$bio -> $bio_title. $bio_tech, you can find me on [Twitter](https://twitter.com/)
$bio_title -> $bio_level $bio_field
$bio_level -> Senior | Junior | Unicorn
$bio_field -> web developer | web designer | food enthusiastic | nose picker
$bio_tech -> In love with the web and Vim
""")

ARTICLE_GRAMMAR = cfg.parse("""
# Article
$article -> $title\\n\\n$punchline\\n\\n$description\\n\\n$content

# Title
$title -># $opening $what $detail $how
$opening -> Must have | The | Essential | Methods for | The jungle of
$what -> HTML5 | Objective-C | GO | Javascript | Scrum | Agile | CSS | Android | Test driven development
$detail -> stack order | hierarchy | training | learning | cherry picking | nipple twisting
$how -> explained | uncovered | analyzed | olympycs


# Punchline
$punchline -> $useless $success just by $cat_action **$cat**. $intro $action *$what*.
$useless -> How to | Think about it, you can | Stop having fear, | Act now, and | You can
$success -> build successful websites | **increase your growth** | increase your traffic | have a low latency API | use less memory | get rid of junk | hack your community
$cat_action -> adding | removing | publishing | connecting | networking | training
$cat -> a cat | some kittens | dogs | a honey badger | a horse | several horses | dolphins
$intro -> Here is a collection of techniques | Read through those useful resources you can use | Learn how | All you need to start your journey
$action -> to learn | to improve | to escalate | to research | to grok | to study


# Description
$description -> $punchline

# Content
$content -> $section\\n$section\\n$section

# Content
$wip_content -> $section

# Section
$section ->## $section_title\\n$links\\n\\n

$section_title -> Why should I consider this? | Language highlights | A different approach

# Links
$links -> $link $link $link | $link $link $link $link | $link $link $link $link $link | $link $link $link $link $link $link

$link ->- [$link_title]($link_url) $link_description\\n

$link_title -> How to check your emails | 5 tips for rapid growth | I'm a dolphin

$link_url -> http://example.com/

$link_description -> $punchline

""")


class Freezable(object):
    def freeze(self):
        for name in dir(self):
            attr = getattr(self, name)
            if isinstance(attr, Freezable):
                val = attr.freeze()
                setattr(self, name, val)

        return self


class Fuzzer(Freezable):
    def fuzz(self):
        raise NotImplementedError()

    def freeze(self):
        return self.fuzz()

    def __call__(self, *args, **kwargs):
        return self.fuzz()


class FuzzyInt(Fuzzer):
    def __init__(self, a, b):
        self.a, self.b = a, b

    def fuzz(self):
        return randint(self.a, self.b)


class FuzzyBool(Fuzzer):
    def fuzz(self):
        return randint(0, 1)


class FuzzyTagTitle(Fuzzer):
    def fuzz(self):
        return GRAMMAR.generate('$tag').lower()


class FuzzyArticleTitle(Fuzzer):
    def fuzz(self):
        return GRAMMAR.generate('$title')


class FuzzyArticlePunchline(Fuzzer):
    def fuzz(self):
        return GRAMMAR.generate('$punchline')


class FuzzyArticleDescription(Fuzzer):
    def fuzz(self):
        return GRAMMAR.generate('$description')


class FuzzyDisplayName(Fuzzer):
    def fuzz(self):
        return GRAMMAR.generate('$display_name')


class FuzzyBio(Fuzzer):
    def fuzz(self):
        return GRAMMAR.generate('$bio')


class FuzzyDateTime(Fuzzer):
    """Random datetime within a given date range."""

    def __init__(self, start_date, end_date=None):
        if end_date is None:
            end_date = datetime.datetime.now()

        if start_date > end_date:
            raise ValueError(
                "FuzzyDateTime boundaries should have start <= end; got %r > %r."
                % (start_date, end_date))

        self.start_date = start_date.toordinal()
        self.end_date = end_date.toordinal()

    def fuzz(self):
        return datetime.date.fromordinal(randint(self.start_date, self.end_date))


class TheFactory(Freezable):
    pk = 0

    def __init__(self, **kwargs):
        self.freeze()
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __call__(self):
        return self.g()

    @classmethod
    def g(cls, how_many=1, up_to=None, kwargs=None):
        if not kwargs:
            kwargs = {}
        if not up_to:
            up_to = how_many

        instances = [cls(**kwargs) for i in range(randint(how_many, up_to))]
        if how_many == 1 and up_to == 1:
            return instances[0]
        return instances


class TheFactoryQuerySet(Freezable):
    up_to = None
    freezed_instances = None

    def __call__(self, *args, **kwargs):
        return self.all()

    def all(self):
        if self.freezed_instances is not None:
            return self.freezed_instances
        elems = self.factory.g(self.how_many, self.up_to)
        return elems

    def freeze(self):
        self.freezed_instances = [e.freeze() for e in self.all()]
        return self.freezed_instances


class TagFactory(TheFactory):
    title = FuzzyTagTitle()
    description = FuzzyArticlePunchline()

    def __unicode__(self):
        return self.title


class TagsQuerySet(TheFactoryQuerySet):
    factory = TagFactory()
    how_many = 1
    up_to = 3


class AuthorFactory(TheFactory):
    display_name = FuzzyDisplayName()
    bio = FuzzyBio()
    website = 'http://example.com/'
    can_publish = True
    score = FuzzyInt(10, 100)
    username = 'pinolo99'
    github_profile_url = 'https://github.com/pinolo99'
    articles_published_count = FuzzyInt(0, 10)
    edits_count = FuzzyInt(10, 100)
    kudos_given_count = FuzzyInt(1, 40)

    @property
    def bio_html(self):
        return markdown.markdown(self.bio)

    def get_absolute_url(self):
        return '/'

    def __unicode__(self):
        return self.display_name


class UserFactory(TheFactory):
    username = 'pinolo99'
    author_profile = AuthorFactory()


class ContributorsFactory(TheFactoryQuerySet):
    factory = UserFactory()
    how_many = 3
    up_to = 30


class ArticleFactory(TheFactory):
    original_author = UserFactory()
    slug = 'this-is-a-title'
    title = FuzzyArticleTitle()
    description = FuzzyArticleDescription()
    punchline = FuzzyArticlePunchline()
    raw_content = 'hello'
    views_count = FuzzyInt(50, 50000)
    received_kudos_count = FuzzyInt(10, 100)
    editors_count = FuzzyInt(1, 10)
    revisions_count = FuzzyInt(2, 100)
    comments_count = FuzzyInt(0, 20)
    is_wiki = False
    is_wip = False
    published_at = FuzzyDateTime(datetime.datetime(2008, 1, 1))
    updated_at = FuzzyDateTime(datetime.datetime(2008, 1, 1))
    other_contributors = ContributorsFactory()

    tags = {'all': TagFactory().g(4)}

    def rendered_html(self):
        html = Article.process_raw_content(ARTICLE_GRAMMAR.generate('$article'))['rendered_html']
        return html

    def is_editable_by_user(self, user):
        return self.is_wiki


class AuthorialArticle(ArticleFactory):
    other_contributors = []


class FullArticle(ArticleFactory):
    def __init__(self, **kwargs):
        md = loader.render_to_string('styleguide/samples/full_article.md')
        content = Article.process_raw_content(md)
        for k, v in content.items():
            setattr(self, k, v)
        super(FullArticle, self).__init__(**kwargs)


class ArticleWiki(ArticleFactory):
    is_wiki = True


class FullArticleUnpublished(FullArticle):
    other_contributors = []
    published_at = None


class ArticleWIP(ArticleFactory):
    is_wiki = True
    is_wip = True


class UnpublishedArticleFactory(ArticleFactory):
    published_at = None


class StyleGuideTemplateView(TemplateView):
    def get_template_names(self):
        return '{}.html'.format(self.kwargs.get('template_name', '').replace(':', '/'))

    def get_context_data(self, **kwargs):
        context_data = super(StyleGuideTemplateView, self).get_context_data(**kwargs)
        t = loader.get_template(self.get_template_names())
        varnodes = t.nodelist.get_nodes_by_type(VariableNode)
        for varname in [x.filter_expression.token for x in varnodes]:
            context_data[varname] = True
        context_data['global_tags'] = TagFactory().g(16)
        return context_data


class StyleGuideTagMenuView(StyleGuideTemplateView):
    def get_template_names(self):
        return 'styleguide/tag_menu.html'

    def get_context_data(self, **kwargs):
        context_data = super(StyleGuideTagMenuView, self).get_context_data(**kwargs)
        context_data['tags'] = TagFactory.g(10)
        return context_data


class StyleGuideLandingView(StyleGuideTemplateView):
    def get_template_names(self):
        return 'landing.html'

    def get_context_data(self, **kwargs):
        articles = []
        articles += ArticleWIP.g(3)
        articles += ArticleWiki.g(3)
        articles += FullArticle.g(3)

        context_data = super(StyleGuideLandingView, self).get_context_data(**kwargs)
        context_data['editors_picks'] = AuthorialArticle.g(6)
        context_data['wip_articles'] = articles
        context_data['article_list'] = articles
        context_data['new_articles'] = articles
        return context_data


class StyleGuideArticleListByTagView(StyleGuideTemplateView):
    def get_template_names(self):
        return 'articles/article_list.html'

    def get_context_data(self, **kwargs):
        context_data = super(StyleGuideArticleListByTagView, self).get_context_data(**kwargs)
        context_data['main_tag'] = TagFactory().g()
        context_data['article_list'] = ArticleFactory().g(10)
        context_data['related_tag_one'] = TagFactory().g()
        context_data['related_articles_one'] = ArticleFactory().g(5)
        context_data['related_tag_two'] = TagFactory().g()
        context_data['related_articles_two'] = ArticleFactory().g(5)
        context_data['related_tags'] = TagFactory().g(10)
        return context_data


class StyleGuideProfileView(StyleGuideTemplateView):
    def get_template_names(self):
        return 'profiles/author_detail.html'

    def get_context_data(self, **kwargs):
        context_data = super(StyleGuideProfileView, self).get_context_data(**kwargs)
        context_data['author_profile'] = AuthorFactory().g()
        context_data['is_public_profile'] = True
        context_data['suggested_wip_articles'] = ArticleFactory(is_wiki=True).g(10)
        context_data['recent_kudos'] = ArticleFactory().g(10)
        context_data['recent_articles_published'] = ArticleFactory().g(10)
        context_data['recent_articles_edited'] = ArticleFactory().g(10)

        return context_data

class StyleGuideMyProfileView(StyleGuideProfileView):
    def get_context_data(self, **kwargs):
        context_data = super(StyleGuideMyProfileView, self).get_context_data(**kwargs)
        context_data['is_public_profile'] = False
        context_data['articles_drafts'] = UnpublishedArticleFactory().g(10)
        context_data['form'] = AuthorForm({'display_name': 'Guglielmo Marino', 'bio': 'This is my bio'})

        return context_data


class StyleGuideMyEmptyProfileView(StyleGuideProfileView):
    def get_context_data(self, **kwargs):
        context_data = super(StyleGuideMyEmptyProfileView, self).get_context_data(**kwargs)
        context_data['author_profile'] = AuthorFactory().g()
        context_data['is_public_profile'] = False
        context_data['form'] = AuthorForm({'display_name': 'Guglielmo Marino', 'bio': 'This is my bio'})
        context_data['recent_kudos'] = []
        context_data['recent_articles_published'] = []
        context_data['recent_articles_edited'] = []

        return context_data


class StyleGuideHistoryView(StyleGuideTemplateView):
    def get_template_names(self):
        return 'article/article_list.html'

    def get_context_data(self, **kwargs):
        context_data = super(StyleGuideHistoryView, self).get_context_data(**kwargs)
        return context_data


class StyleGuideArticleView(StyleGuideTemplateView):
    def get_template_names(self):
        return 'articles/article_detail.html'

    def get_context_data(self, **kwargs):
        context_data = super(StyleGuideArticleView, self).get_context_data(**kwargs)
        context_data['article'] = ArticleFactory.g()
        context_data['related_tag_one'] = TagFactory().g()
        context_data['related_articles_one'] = ArticleFactory().g(5)
        context_data['related_tag_two'] = TagFactory().g()
        context_data['related_articles_two'] = ArticleFactory().g(5)
        context_data['read_more'] = ArticleFactory().g(5)
        return context_data


class StyleGuideFullArticleView(StyleGuideArticleView):
    def get_context_data(self, **kwargs):
        context_data = super(StyleGuideFullArticleView, self).get_context_data(**kwargs)
        context_data['article'] = FullArticle.g()
        return context_data


class StyleGuideFullArticleWikiView(StyleGuideArticleView):
    def get_context_data(self, **kwargs):
        context_data = super(StyleGuideFullArticleWikiView, self).get_context_data(**kwargs)
        context_data['article'] = ArticleWiki.g()
        return context_data


class StyleGuideArticleWIPView(StyleGuideArticleView):
    def get_context_data(self, **kwargs):
        context_data = super(StyleGuideArticleWIPView, self).get_context_data(**kwargs)
        context_data['article'] = ArticleWIP.g()
        return context_data


class StyleGuideArticleUnpublishedView(StyleGuideArticleView):
    def get_context_data(self, **kwargs):
        context_data = super(StyleGuideArticleUnpublishedView, self).get_context_data(**kwargs)
        context_data['article'] = FullArticleUnpublished.g()
        return context_data


class StyleGuideArticleFormView(ArticleCreateView):
    def dispatch(self, request, *args, **kwargs):
        return super(CreateView, self).dispatch(request, *args, **kwargs)

