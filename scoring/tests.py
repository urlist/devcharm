from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.test import TestCase
from django_dynamic_fixture import G
import mock
from scoring.decorators import score_change, score_check, score_produce, score_consume


User = get_user_model()


class TestScoreGenerationConsumption(TestCase):
    def setUp(self):
        self.user = G(User)

    def test_decorator_can_be_applied(self):
        # The basic assumption is that most score-related operations will be on views.
        request = mock.MagicMock()
        # mock does not support __name__ at the moment, so...
        view_func = mock.MagicMock(return_value=HttpResponse(), __name__="irrelevant")
        view = score_change(view_func)
        # the basic requirement is that the view gets called, of course
        response = view(request)
        self.assertTrue(view_func.called)
        self.assertEqual(response.status_code, 200)

        # Checking that it can be applied as factory
        decorator = score_change(increment=1)
        view = decorator(view_func)
        self.assertTrue(view_func.called)
        self.assertEqual(response.status_code, 200)

    def test_decorator_updates_user_score(self):
        request = mock.MagicMock()
        view_func = mock.MagicMock(return_value=HttpResponse(), __name__="irrelevant")
        view = score_change(view_func, 10)
        request.user = self.user
        request.user.author_profile.score = 0
        response = view(request)
        self.assertEqual(request.user.author_profile.score, 10)

        # Unauthenticated users should have no score change
        request.user.is_authenticated = lambda: False
        response = view(request)
        self.assertEqual(request.user.author_profile.score, 10)

    def test_decorator_accepts_lambdas_with_request(self):
        request = mock.MagicMock()
        view_func = mock.MagicMock(return_value=HttpResponse(), __name__="irrelevant")
        view = score_change(view_func, increment_func=lambda req: 10)
        request.user = self.user
        request.user.author_profile.score = 0
        response = view(request)
        self.assertEqual(request.user.author_profile.score, 10)
        # A decorator with both the value and the func should accept both and apply both
        view = score_change(view_func, increment=5, increment_func=lambda req: 10)
        request.user.author_profile.score = 0
        response = view(request)
        self.assertEqual(request.user.author_profile.score, 15)
        # Increment_func must be applied only when the user is authenticated, of course
        request.user.author_profile.score = 0
        request.user.is_authenticated = lambda: False
        response = view(request)
        self.assertEqual(request.user.author_profile.score, 0)

    def test_decorator_saves_changes(self):
        def arbitrary_view_func(*args, **kwargs):
            return HttpResponse()
        request = mock.MagicMock(user=self.user)  # This time, it's important it's an actual user instance
        view = score_change(arbitrary_view_func, increment_func=lambda req: 10, increment=8)
        self.assertFalse(request.user.scoretransaction_set.exists())
        response = view(request)
        # First, we check that there's actually a record
        self.assertTrue(request.user.scoretransaction_set.exists())
        score_transaction = request.user.scoretransaction_set.latest()
        # Then, that the record has the correct value both for change and for event
        self.assertEqual(score_transaction.change, 18)
        self.assertEqual(score_transaction.operation, 'arbitrary_view_func')
        # We should also allow a name to be set for specific circumstances
        view = score_change(arbitrary_view_func, increment_func=lambda req: 10, increment=8, operation="Random stuff")
        response = view(request)
        score_transaction = request.user.scoretransaction_set.latest()
        self.assertEqual(score_transaction.operation, 'Random stuff')

    def test_score_decorators_accept_callable_for_operation(self):
        def arbitrary_view_func(*args, **kwargs):
            return HttpResponse()
        request = mock.MagicMock(user=self.user)  # This time, it's important it's an actual user instance
        view = score_change(arbitrary_view_func, increment=8, operation=lambda r: "Result of lambda")
        response = view(request)
        score_transaction = request.user.scoretransaction_set.latest()
        self.assertEqual(score_transaction.operation, "Result of lambda")

    def test_user_score_tracks_transactions(self):
        self.assertTrue(hasattr(self.user.author_profile, 'score'))
        self.assertTrue(hasattr(self.user, 'scoretransaction_set'))
        score = self.user.author_profile.score
        self.user.scoretransaction_set.create(change=100)
        self.user = User.objects.get(pk=self.user.pk)
        self.assertEqual(self.user.author_profile.score, score+100)

    def test_shortcuts(self):
        def arbitrary_view_func(*args, **kwargs):
            return HttpResponse()
        request = mock.MagicMock(user=self.user)
        score = self.user.author_profile.score
        # Increment decorator
        view = score_produce(arbitrary_view_func, 100)
        response = view(request)
        self.assertEqual(request.user.author_profile.score, score+100)
        view = score_produce(arbitrary_view_func, lambda req: 100)
        response = view(request)
        self.assertEqual(request.user.author_profile.score, score+200)

        # Decrement decorator
        view = score_consume(arbitrary_view_func, 100)
        response = view(request)
        self.assertEqual(request.user.author_profile.score, score+100)
        # A decrement decorator with a negative value does not really make sense
        self.assertRaises(ImproperlyConfigured, lambda: score_consume(arbitrary_view_func, -100))

    def test_consume_decorator_fails_if_user_doesnt_have_required_score(self):
        request = mock.MagicMock(user=self.user)
        view_func = mock.MagicMock(return_value=HttpResponse(), __name__="irrelevant")
        view = score_consume(view_func, 100)
        response = view(request)
        self.assertFalse(view_func.called)
        # This operation should result in an error, anyway
        self.assertEqual(response.status_code, 403)  # Forbidden makes sense


class TestScoreChecks(TestCase):
    def test_decorator_can_be_applied(self):
        # The basic assumption is that most score-related operations will be on views.
        request = mock.MagicMock()
        view_func = mock.MagicMock(return_value=HttpResponse())
        view = score_check(view_func)
        response = view(request)
        self.assertTrue(view_func.called)
        self.assertEqual(response.status_code, 200)

    def test_decorated_views_require_minimum_score_and_login(self):
        request = mock.MagicMock()
        view_func = mock.MagicMock(return_value=HttpResponse())
        view = score_check(view_func, 10)
        # Not authenticated
        request.user.is_authenticated = lambda: False
        response = view(request)
        self.assertFalse(view_func.called)
        # Authenticated but not enough score
        request.user.is_authenticated = lambda: True
        request.user.score = 0
        response = view(request)
        self.assertFalse(view_func.called)
        # Authenticated and enough score -> view called
        request.user.score = 100
        response = view(request)
        self.assertTrue(view_func.called)

    def test_scorecheck_failed_redirects_to_login_or_custom_url(self):
        request = mock.MagicMock()
        view_func = mock.MagicMock(return_value=HttpResponse())
        view = score_check(view_func, 10)
        request.user.is_authenticated = lambda: True
        request.user.score = 0
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, settings.LOGIN_URL)
        view = score_check(view_func, 10, redirect_url='/random')
        response = view(request)
        self.assertEqual(response.url, '/random')