from django.test import RequestFactory, TestCase

from allianceauth import views

from .auth_utils import AuthUtils


class TestCustomErrorHandlerViews(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = AuthUtils.create_user("my_user")
        cls.factory = RequestFactory()

    def test_should_return_status_code_400(self):
        # give
        request = self.factory.get("/")
        request.user = self.user
        # when
        response = views.Generic400Redirect(request)
        # then
        self.assertEqual(response.status_code, 400)

    def test_should_return_status_code_403(self):
        # give
        request = self.factory.get("/")
        request.user = self.user
        # when
        response = views.Generic403Redirect(request)
        # then
        self.assertEqual(response.status_code, 403)

    def test_should_return_status_code_404(self):
        # give
        request = self.factory.get("/")
        request.user = self.user
        # when
        response = views.Generic404Redirect(request)
        # then
        self.assertEqual(response.status_code, 404)

    def test_should_return_status_code_500(self):
        # give
        request = self.factory.get("/")
        request.user = self.user
        # when
        response = views.Generic500Redirect(request)
        # then
        self.assertEqual(response.status_code, 500)
