"""
Test sentinel user
"""

import re

# Django
from django.contrib.auth.models import User
from django.test import TestCase

# Alliance Auth
from allianceauth.framework.api.user import (
    get_sentinel_user,
    get_main_character_from_user,
    get_main_character_name_from_user
)
from allianceauth.tests.auth_utils import AuthUtils


class TestSentinelUser(TestCase):
    """
    Tests for the sentinel user
    """

    def test_should_create_user_when_it_does_not_exist(self) -> None:
        """
        Test should create a sentinel user when it doesn't exist

        :return:
        :rtype:
        """

        # when
        user = get_sentinel_user()

        # then
        self.assertEqual(first=user.username, second="deleted")

    def test_should_return_user_when_it_does(self) -> None:
        """
        Test should return sentinel user when it exists

        :return:
        :rtype:
        """

        # given
        User.objects.create_user(username="deleted")

        # when
        user = get_sentinel_user()

        # then
        self.assertEqual(first=user.username, second="deleted")


class TestGetMainForUser(TestCase):
    """
    Tests for get_main_character_from_user
    """

    @classmethod
    def setUpClass(cls) -> None:
        """
        Set up groups and users
        """

        super().setUpClass()

        cls.character_name = "William T. Riker"
        cls.character_name_2 = "Christopher Pike"

        cls.username = re.sub(pattern=r"[^\w\d@\.\+-]", repl="_", string=cls.character_name)
        cls.username_2 = re.sub(
            pattern=r"[^\w\d@\.\+-]", repl="_", string=cls.character_name_2
        )

        cls.user = AuthUtils.create_user(username=cls.username)
        cls.user_without_main = AuthUtils.create_user(
            username=cls.username_2, disconnect_signals=True
        )

        cls.character = AuthUtils.add_main_character_2(
            user=cls.user, name=cls.character_name, character_id=1001
        )


    def test_get_main_character_from_user_should_return_character_name(self):
        """
        Test should return the main character name for a regular user

        :return:
        :rtype:
        """

        character = get_main_character_from_user(user=self.user)

        self.assertEqual(first=character, second=self.character)


    def test_get_main_character_from_user_should_return_none_for_no_main_character(self):
        """
        Test should return None for User without a main character

        :return:
        :rtype:
        """

        character = get_main_character_from_user(user=self.user_without_main)

        self.assertIsNone(obj=character)


    def test_get_main_character_from_user_should_none(self):
        """
        Test should return None when user is None

        :return:
        :rtype:
        """

        user = None

        character = get_main_character_from_user(user=user)

        self.assertIsNone(obj=character)


    def test_get_main_character_name_from_user_should_return_character_name(self):
        """
        Test should return the main character name for a regular user

        :return:
        :rtype:
        """

        character_name = get_main_character_name_from_user(user=self.user)

        self.assertEqual(first=character_name, second=self.character_name)

    def test_get_main_character_name_from_user_should_return_user_name(self):
        """
        Test should return just the username for a user without a main character

        :return:
        :rtype:
        """

        character_name = get_main_character_name_from_user(user=self.user_without_main)

        self.assertEqual(first=character_name, second=self.username_2)

    def test_get_main_character_name_from_user_should_return_sentinel_user(self):
        """
        Test should return "deleted" as username (Sentinel User)

        :return:
        :rtype:
        """

        user = get_sentinel_user()

        character_name = get_main_character_name_from_user(user=user)

        self.assertEqual(first=character_name, second="deleted")

    def test_get_main_character_name_from_user_should_return_sentinel_user_for_none(self):
        """
        Test should return "deleted" (Sentinel User) if user is None

        :return:
        :rtype:
        """

        user = None

        character_name = get_main_character_name_from_user(user=user)

        self.assertEqual(first=character_name, second="deleted")
