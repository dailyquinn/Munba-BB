"""
Test sentinel user
"""

import json
import re

# Django
from allianceauth.tests.auth_utils import AuthUtils
from django.test import RequestFactory, TestCase
from django.http import HttpRequest
# Alliance Auth
from allianceauth.framework.datatables import DataTablesView
from allianceauth.eveonline.models import EveCharacter

class TestView(DataTablesView):
    model=EveCharacter
    columns = [
        ("", "{{ row.character_id }}"),
        ("character_name", "{{ row.character_name }}"),
        ("corporation_name", "{{ row.corporation_name }}"),
        ("alliance_name", "{{ row.alliance_name }}"),
    ]

class TestDataTables(TestCase):
    def setUp(self):
        self.get_params = {
            'draw': '1',
            'columns[0][data]': '0',
            'columns[0][name]': '',
            'columns[0][searchable]': 'false',
            'columns[0][orderable]': 'false',
            'columns[0][search][value]': '',
            'columns[0][search][regex]': 'false',
            'columns[1][data]': '1',
            'columns[1][name]': '',
            'columns[1][searchable]': 'true',
            'columns[1][orderable]': 'true',
            'columns[1][search][value]': '',
            'columns[1][search][regex]': 'false',
            'columns[2][data]': '2',
            'columns[2][name]': '',
            'columns[2][searchable]': 'true',
            'columns[2][orderable]': 'false',
            'columns[2][search][value]': '',
            'columns[2][search][regex]': 'false',
            'columns[3][data]': '3',
            'columns[3][name]': '',
            'columns[3][searchable]': 'true',
            'columns[3][orderable]': 'true',
            'columns[3][search][value]': '',
            'columns[3][search][regex]': 'false',
            'order[0][column]': '1',
            'order[0][dir]': 'asc',
            'start': '0',
            'length': '10',
            'search[value]': '',
            'search[regex]': 'false',
            '_': '123456789'
        }


    @classmethod
    def setUpClass(cls) -> None:
        """
        Set up eve models
        """

        super().setUpClass()
        cls.factory = RequestFactory()

        cls.user = AuthUtils.create_user("bruce_wayne")
        cls.user.is_superuser = True
        cls.user.save()

        EveCharacter.objects.all().delete()
        for i in range(1,16):
            EveCharacter.objects.create(
                character_id=1000+i,
                character_name=f"{1000+i} - Test Character - {1000+i}",
                corporation_id=2000+i,
                corporation_name=f"{2000+i} - Test Corporation",
            )

        for i in range(16,21):
            EveCharacter.objects.create(
                character_id=1000+i,
                character_name=f"{1000+i} - Test Character - {1000+i}",
                corporation_id=2000+i,
                corporation_name=f"{2000+i} - Test Corporation",
                alliance_id=3000+i,
                alliance_name=f"{3000+i} - Test Alliance",
            )


    def test_view_default(self):
        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(data[0][0], "1001")
        self.assertEqual(data[9][0], "1010")

    def test_view_reverse_sort(self):
        self.get_params["order[0][dir]"] = "desc"
        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(data[0][0], "1020")
        self.assertEqual(data[9][0], "1011")

    def test_view_no_sort(self):
        self.get_params.pop("order[0][column]")
        self.get_params.pop("order[0][dir]")
        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(data[0][0], "1001")
        self.assertEqual(data[9][0], "1010")

    def test_view_non_sortable_sort(self):
        self.get_params["order[0][dir]"] = "desc"
        self.get_params["order[0][column]"] = "0"
        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(data[0][0], "1001")
        self.assertEqual(data[9][0], "1010")

    def test_view_20_rows(self):
        self.get_params["length"] = "20"
        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(data[0][0], "1001")
        self.assertEqual(data[19][0], "1020")

    def test_records_filtered(self):
        self.get_params["length"] = "20"
        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        content = json.loads(response.get(request).content)
        self.assertEqual(content["recordsFiltered"], 20)
        self.assertEqual(content["recordsTotal"], 20)

    def test_view_global_search(self):
        self.get_params["search[value]"] = "1020"
        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0][0], "1020")

    def test_view_col_1_search(self):
        self.get_params["columns[1][search][value]"] = "1020"
        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0][0], "1020")

    def test_view_col_1_search_empty(self):
        self.get_params["columns[1][search][value]"] = "zzz"

        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(len(data), 0)

    def test_view_cc_3_search_empty(self):
        self.get_params["columns[3][columnControl][search][value]"] = ""
        self.get_params["columns[3][columnControl][search][logic]"] = "empty"
        self.get_params["columns[3][columnControl][search][type]"] = "text"
        self.get_params["length"] = "20"

        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(len(data), 15)

    def test_view_cc_3_search_not_empty(self):
        self.get_params["columns[3][columnControl][search][value]"] = ""
        self.get_params["columns[3][columnControl][search][logic]"] = "notEmpty"
        self.get_params["columns[3][columnControl][search][type]"] = "text"
        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(len(data), 5)

    def test_view_cc_1_search_ends_with(self):
        self.get_params["columns[1][columnControl][search][value]"] = "9"
        self.get_params["columns[1][columnControl][search][logic]"] = "ends"
        self.get_params["columns[1][columnControl][search][type]"] = "text"
        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(len(data), 2)

    def test_view_cc_1_search_starts_with(self):
        self.get_params["columns[1][columnControl][search][value]"] = "1009"
        self.get_params["columns[1][columnControl][search][logic]"] = "starts"
        self.get_params["columns[1][columnControl][search][type]"] = "text"
        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(len(data), 1)

    def test_view_cc_1_search_not_contains(self):
        self.get_params["columns[1][columnControl][search][value]"] = "100"
        self.get_params["columns[1][columnControl][search][logic]"] = "notContains"
        self.get_params["columns[1][columnControl][search][type]"] = "text"
        self.get_params["length"] = "20"
        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(len(data), 11)

    def test_view_cc_1_search_contains(self):
        self.get_params["columns[1][columnControl][search][value]"] = "100"
        self.get_params["columns[1][columnControl][search][logic]"] = "contains"
        self.get_params["columns[1][columnControl][search][type]"] = "text"
        self.get_params["length"] = "20"
        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(len(data), 9)

    def test_view_cc_1_search_equal(self):
        self.get_params["columns[1][columnControl][search][value]"] = "1001 - Test Character - 1001"
        self.get_params["columns[1][columnControl][search][logic]"] = "equal"
        self.get_params["columns[1][columnControl][search][type]"] = "text"
        self.get_params["length"] = "20"
        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(len(data), 1)

    def test_view_cc_1_search_not_equal(self):
        self.get_params["columns[1][columnControl][search][value]"] = "1001 - Test Character - 1001"
        self.get_params["columns[1][columnControl][search][logic]"] = "notEqual"
        self.get_params["columns[1][columnControl][search][type]"] = "text"
        self.get_params["length"] = "20"
        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(len(data), 19)

    def test_view_cc_no_pagination(self):
        self.get_params["length"] = "-1"
        self.client.force_login(self.user)
        request = self.factory.get('/fake-url/', data=self.get_params)
        response = TestView()
        response.setup(request)
        data = json.loads(response.get(request).content)["data"]
        self.assertEqual(len(data), 20)
