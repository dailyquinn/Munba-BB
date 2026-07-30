from unittest import mock

from django.test import TestCase, RequestFactory
from django import urls
from django.contrib.auth.models import User, Group, Permission
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import signals
from django.contrib.admin import AdminSite

from allianceauth.tests.auth_utils import AuthUtils
from .auth_hooks import Teamspeak3Service
from .models import Teamspeak3User, AuthTS, TSgroup, StateGroup
from .tasks import Teamspeak3Tasks
from .signals import m2m_changed_authts_group, post_save_authts, post_delete_authts
from .admin import AuthTSgroupAdmin

from .manager import Teamspeak3Manager
from .util.ts3 import TeamspeakError
from allianceauth.groupmanagement.models import ReservedGroupName

MODULE_PATH = 'allianceauth.services.modules.teamspeak3'
DEFAULT_AUTH_GROUP = 'Member'


def add_permissions():
    permission = Permission.objects.get(codename='access_teamspeak3')
    members = Group.objects.get_or_create(name=DEFAULT_AUTH_GROUP)[0]
    AuthUtils.add_permissions_to_groups([permission], [members])


class Teamspeak3HooksTestCase(TestCase):
    def setUp(self):
        # Inert signals before setup begins
        with mock.patch(MODULE_PATH + '.signals.trigger_all_ts_update') as trigger_all_ts_update:
            self.member = 'member_user'
            member = AuthUtils.create_member(self.member)
            Teamspeak3User.objects.create(user=member, uid=self.member, perm_key='123ABC')
            self.none_user = 'none_user'
            AuthUtils.create_user(self.none_user)
            state = member.profile.state
            ts_member_group = TSgroup.objects.create(ts_group_id=1, ts_group_name='Member')
            ts_state_group = TSgroup.objects.create(ts_group_id=2, ts_group_name='State')
            m2m_member_group = AuthTS.objects.create(auth_group=member.groups.all()[0])
            m2m_member_group.ts_group.add(ts_member_group)
            m2m_member_group.save()
            StateGroup.objects.create(state=state, ts_group=ts_state_group)
            self.service = Teamspeak3Service
            add_permissions()

    def test_has_account(self):
        member = User.objects.get(username=self.member)
        none_user = User.objects.get(username=self.none_user)
        self.assertTrue(Teamspeak3Tasks.has_account(member))
        self.assertFalse(Teamspeak3Tasks.has_account(none_user))

    def test_service_enabled(self):
        service = self.service()
        member = User.objects.get(username=self.member)
        none_user = User.objects.get(username=self.none_user)

        self.assertTrue(service.service_active_for_user(member))
        self.assertFalse(service.service_active_for_user(none_user))

    @mock.patch(MODULE_PATH + '.tasks.Teamspeak3Manager')
    def test_update_all_groups(self, manager):
        instance = manager.return_value.__enter__.return_value
        service = self.service()
        service.update_all_groups()
        # Check user has groups updated
        self.assertTrue(instance.update_groups.called)
        self.assertEqual(instance.update_groups.call_count, 1)

    def test_update_groups(self):
        # Check member has Member group updated
        with mock.patch(MODULE_PATH + '.tasks.Teamspeak3Manager') as manager:
            instance = manager.return_value.__enter__.return_value
            service = self.service()
            member = User.objects.get(username=self.member)
            service.update_groups(member)
            self.assertTrue(instance.update_groups.called)
            args, kwargs = instance.update_groups.call_args
            # update_groups(user.teamspeak3.uid, groups)
            self.assertEqual({'Member': 1, 'State': 2}, args[1])  # Check groups
            self.assertEqual(self.member, args[0])  # Check uid

        # Check none user does not have groups updated
        with mock.patch(MODULE_PATH + '.tasks.Teamspeak3Manager') as manager:
            service = self.service()
            none_user = User.objects.get(username=self.none_user)
            service.update_groups(none_user)
            self.assertFalse(manager.return_value.__enter__.return_value.update_user_groups.called)

    @mock.patch(MODULE_PATH + '.tasks.Teamspeak3Manager')
    def test_validate_user(self, manager):
        service = self.service()
        # Test member is not deleted
        member = User.objects.get(username=self.member)
        service.validate_user(member)
        self.assertTrue(member.teamspeak3)

        # Test none user is deleted
        none_user = User.objects.get(username=self.none_user)
        Teamspeak3User.objects.create(user=none_user, uid='abc123', perm_key='132ACB')
        service.validate_user(none_user)
        self.assertTrue(manager.return_value.__enter__.return_value.delete_user.called)
        with self.assertRaises(ObjectDoesNotExist):
            none_teamspeak3 = User.objects.get(username=self.none_user).teamspeak3

    @mock.patch(MODULE_PATH + '.tasks.Teamspeak3Manager')
    def test_delete_user(self, manager):
        member = User.objects.get(username=self.member)

        service = self.service()
        result = service.delete_user(member)

        self.assertTrue(result)
        self.assertTrue(manager.return_value.__enter__.return_value.delete_user.called)
        with self.assertRaises(ObjectDoesNotExist):
            teamspeak3_user = User.objects.get(username=self.member).teamspeak3

    def test_render_services_ctrl(self):
        service = self.service()
        member = User.objects.get(username=self.member)
        request = RequestFactory().get('/services/')
        request.user = member

        response = service.render_services_ctrl(request)
        self.assertTemplateUsed(service.service_ctrl_template)
        self.assertIn(urls.reverse('teamspeak3:deactivate'), response)
        self.assertIn(urls.reverse('teamspeak3:reset_perm'), response)

        # Test register becomes available
        member.teamspeak3.delete()
        member = User.objects.get(username=self.member)
        request.user = member
        response = service.render_services_ctrl(request)
        self.assertIn(urls.reverse('teamspeak3:activate'), response)


class Teamspeak3ViewsTestCase(TestCase):
    def setUp(self):
        # Inert signals before setup begins
        with mock.patch(MODULE_PATH + '.signals.trigger_all_ts_update') as trigger_all_ts_update:
            self.member = AuthUtils.create_member('auth_member')
            self.member.email = 'auth_member@example.com'
            self.member.save()
            AuthUtils.add_main_character(self.member, 'auth_member', '12345', corp_id='111', corp_name='Test Corporation')

            ts_member_group = TSgroup.objects.create(ts_group_id=1, ts_group_name='Member')
            m2m_member = AuthTS.objects.create(auth_group=Group.objects.get(name='Member'))
            m2m_member.ts_group.add(ts_member_group)
            m2m_member.save()
            add_permissions()

    def login(self, user=None, password=None):
        if user is None:
            user = self.member
        self.client.force_login(user)

    @mock.patch(MODULE_PATH + '.forms.Teamspeak3Manager')
    @mock.patch(MODULE_PATH + '.views.Teamspeak3Manager')
    def test_activate(self, manager, forms_manager):
        self.login()
        expected_username = 'auth_member'
        instance = manager.return_value.__enter__.return_value
        instance.add_user.return_value = (expected_username, 'abc123')

        response = self.client.get(urls.reverse('teamspeak3:activate'))

        self.assertTrue(instance.add_user.called)
        teamspeak3_user = Teamspeak3User.objects.get(user=self.member)
        self.assertTrue(teamspeak3_user.uid)
        self.assertTrue(teamspeak3_user.perm_key)
        self.assertRedirects(response, urls.reverse('teamspeak3:verify'), target_status_code=200)

    @mock.patch(MODULE_PATH + '.forms.Teamspeak3Manager')
    @mock.patch(MODULE_PATH + '.tasks.Teamspeak3Manager')
    def test_verify_submit(self, manager, forms_manager):
        self.login()
        expected_username = 'auth_member'

        forms_instance = manager.return_value.__enter__.return_value
        forms_instance._get_userid.return_value = '1234'

        Teamspeak3User.objects.update_or_create(user=self.member, defaults={'uid': '1234', 'perm_key': '5678'})
        data = {'username': 'auth_member'}

        response = self.client.post(urls.reverse('teamspeak3:verify'), data)

        self.assertRedirects(response, urls.reverse('services:services'), target_status_code=200)
        self.assertTrue(manager.return_value.__enter__.return_value.update_groups.called)

    @mock.patch(MODULE_PATH + '.tasks.Teamspeak3Manager')
    def test_deactivate(self, manager):
        self.login()
        Teamspeak3User.objects.create(user=self.member, uid='some member')

        response = self.client.get(urls.reverse('teamspeak3:deactivate'))

        self.assertTrue(manager.return_value.__enter__.return_value.delete_user.called)
        self.assertRedirects(response, expected_url=urls.reverse('services:services'), target_status_code=200)
        with self.assertRaises(ObjectDoesNotExist):
            teamspeak3_user = User.objects.get(pk=self.member.pk).teamspeak3

    @mock.patch(MODULE_PATH + '.tasks.Teamspeak3Manager')
    @mock.patch(MODULE_PATH + '.views.Teamspeak3Manager')
    def test_reset_perm(self, manager, tasks_manager):
        self.login()
        Teamspeak3User.objects.create(user=self.member, uid='some member')

        manager.return_value.__enter__.return_value.generate_new_permissionkey.return_value = "valid_member", "123abc"

        response = self.client.get(urls.reverse('teamspeak3:reset_perm'))

        self.assertRedirects(response, urls.reverse('services:services'), target_status_code=200)
        ts3_user = Teamspeak3User.objects.get(uid='valid_member')
        self.assertEqual(ts3_user.uid, 'valid_member')
        self.assertEqual(ts3_user.perm_key, '123abc')
        self.assertTrue(tasks_manager.return_value.__enter__.return_value.update_groups.called)

    @mock.patch(MODULE_PATH + '.views.Teamspeak3Tasks')
    @mock.patch(MODULE_PATH + '.views.messages')
    def test_should_update_ts_groups(self, messages, Teamspeak3Tasks):
        # given
        self.member.is_superuser = True
        self.member.is_staff = True
        self.member.save()
        self.login()
        # when
        response = self.client.get(urls.reverse('teamspeak3:admin_update_ts3_groups'))
        # then
        self.assertRedirects(
            response, urls.reverse('admin:teamspeak3_authts_changelist'),
            target_status_code=200
        )
        self.assertTrue(messages.info.called)
        self.assertTrue(Teamspeak3Tasks.run_ts3_group_update.delay.called)


class Teamspeak3SignalsTestCase(TestCase):
    def setUp(self):
        self.member = AuthUtils.create_member('auth_member')

        # Suppress signals action while setting up
        with mock.patch(MODULE_PATH + '.signals.trigger_all_ts_update') as trigger_all_ts_update:
            ts_member_group = TSgroup.objects.create(ts_group_id=1, ts_group_name='Member')
            self.m2m_member = AuthTS.objects.create(auth_group=Group.objects.get(name='Member'))
            self.m2m_member.ts_group.add(ts_member_group)
            self.m2m_member.save()

    def test_m2m_signal_registry(self):
        """
        Test that the m2m signal has been registered
        """
        registered_functions = [r[1]() for r in signals.m2m_changed.receivers]
        self.assertIn(m2m_changed_authts_group, registered_functions)

    def test_post_save_signal_registry(self):
        """
        Test that the post_save signal has been registered
        """
        registered_functions = [r[1]() for r in signals.post_save.receivers]
        self.assertIn(post_save_authts, registered_functions)

    def test_post_delete_signal_registry(self):
        """
        Test that the post_delete signal has been registered
        """
        registered_functions = [r[1]() for r in signals.post_delete.receivers]
        self.assertIn(post_delete_authts, registered_functions)

    @mock.patch(MODULE_PATH + '.signals.transaction')
    @mock.patch(MODULE_PATH + '.signals.trigger_all_ts_update')
    def test_m2m_changed_authts_group(self, trigger_all_ts_update, transaction):

        # Overload transaction.on_commit so everything happens synchronously
        transaction.on_commit = lambda fn: fn()

        new_group = TSgroup.objects.create(ts_group_id=99, ts_group_name='new TS group')
        self.m2m_member.ts_group.add(new_group)
        self.m2m_member.save()  # Triggers signal

        self.assertTrue(trigger_all_ts_update.called)

    @mock.patch(MODULE_PATH + '.signals.transaction')
    @mock.patch(MODULE_PATH + '.signals.trigger_all_ts_update')
    def test_post_save_authts(self, trigger_all_ts_update, transaction):

        # Overload transaction.on_commit so everything happens synchronously
        transaction.on_commit = lambda fn: fn()

        AuthTS.objects.create(auth_group=Group.objects.create(name='Test Group'))  # Trigger signal (AuthTS creation)

        self.assertTrue(trigger_all_ts_update.called)

    @mock.patch(MODULE_PATH + '.signals.transaction')
    @mock.patch(MODULE_PATH + '.signals.trigger_all_ts_update')
    def test_post_delete_authts(self, trigger_all_ts_update, transaction):
        # Overload transaction.on_commit so everything happens synchronously
        transaction.on_commit = lambda fn: fn()

        self.m2m_member.delete()  # Trigger delete signal

        self.assertTrue(trigger_all_ts_update.called)

    @mock.patch(MODULE_PATH + '.signals.transaction')
    @mock.patch(MODULE_PATH + '.signals.Teamspeak3Tasks.update_groups.delay')
    def test_state_changed(self, update_groups, transaction):
        # Overload transaction.on_commit so everything happens synchronously
        transaction.on_commit = lambda fn: fn()

        state = AuthUtils.create_state('test', 1000, disconnect_signals=True)
        self.member.profile.state = state
        self.member.profile.save()

        self.assertTrue(update_groups.called)


class Teamspeak3ManagerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.reserved = ReservedGroupName.objects.create(name='reserved', reason='tests', created_by='Bob, praise be!')

    @staticmethod
    def my_side_effect(*args, **kwargs):
        raise TeamspeakError(1)

    @mock.patch.object(Teamspeak3Manager, '_group_list')
    @mock.patch.object(Teamspeak3Manager, '_group_id_by_name')
    def test_add_user_exception(self, _group_id_by_name, _group_list):
        """test 1st exception occuring in add_user()"""
        # set mocks in Teamspeak3Manager class
        _group_list.return_value = ['Member', 'Guest']
        _group_id_by_name.return_value =  99
        manager = Teamspeak3Manager()
        server = mock.MagicMock()
        server._connected.return_value = True
        server.send_command = mock.Mock(side_effect=Teamspeak3ManagerTestCase.my_side_effect)
        manager._server = server

        # create test data
        user = AuthUtils.create_user("dummy")
        AuthUtils.assign_state(user, AuthUtils.get_member_state())

        # perform test
        manager.add_user(user, "Dummy User")

    @mock.patch.object(Teamspeak3Manager, '_get_userid')
    @mock.patch.object(Teamspeak3Manager, '_user_group_list')
    @mock.patch.object(Teamspeak3Manager, '_add_user_to_group')
    @mock.patch.object(Teamspeak3Manager, '_remove_user_from_group')
    def test_update_groups_add(self, remove, add, groups, userid):
        """Add to one group"""
        userid.return_value = 1
        groups.return_value = {'test': 1}

        Teamspeak3Manager().update_groups(1, {'test': 1, 'dummy': 2})
        self.assertEqual(add.call_count, 1)
        self.assertEqual(remove.call_count, 0)
        self.assertEqual(add.call_args[0][1], 2)

    @mock.patch.object(Teamspeak3Manager, '_get_userid')
    @mock.patch.object(Teamspeak3Manager, '_user_group_list')
    @mock.patch.object(Teamspeak3Manager, '_add_user_to_group')
    @mock.patch.object(Teamspeak3Manager, '_remove_user_from_group')
    def test_update_groups_remove(self, remove, add, groups, userid):
        """Remove from one group"""
        userid.return_value = 1
        groups.return_value = {'test': '1', 'dummy': '2'}

        Teamspeak3Manager().update_groups(1, {'test': 1})
        self.assertEqual(add.call_count, 0)
        self.assertEqual(remove.call_count, 1)
        self.assertEqual(remove.call_args[0][1], 2)

    @mock.patch.object(Teamspeak3Manager, '_get_userid')
    @mock.patch.object(Teamspeak3Manager, '_user_group_list')
    @mock.patch.object(Teamspeak3Manager, '_add_user_to_group')
    @mock.patch.object(Teamspeak3Manager, '_remove_user_from_group')
    def test_update_groups_remove_reserved(self, remove, add, groups, userid):
        """Remove from one group, but do not touch reserved group"""
        userid.return_value = 1
        groups.return_value = {'test': 1, 'dummy': 2, self.reserved.name: 3}

        Teamspeak3Manager().update_groups(1, {'test': 1})
        self.assertEqual(add.call_count, 0)
        self.assertEqual(remove.call_count, 1)
        self.assertEqual(remove.call_args[0][1], 2)

    @mock.patch.object(Teamspeak3Manager, '_group_list')
    def test_sync_group_db_create(self, group_list):
        """Populate the list of all TSgroups"""
        group_list.return_value = {'allowed':'1', 'also allowed':'2'}
        Teamspeak3Manager()._sync_ts_group_db()
        self.assertEqual(TSgroup.objects.all().count(), 2)

    @mock.patch.object(Teamspeak3Manager, '_group_list')
    def test_sync_group_db_delete(self, group_list):
        """Populate the list of all TSgroups, and delete one which no longer exists"""
        TSgroup.objects.create(ts_group_name='deleted', ts_group_id=3)
        group_list.return_value = {'allowed': '1'}
        Teamspeak3Manager()._sync_ts_group_db()
        self.assertEqual(TSgroup.objects.all().count(), 1)
        self.assertFalse(TSgroup.objects.filter(ts_group_name='deleted').exists())

    @mock.patch.object(Teamspeak3Manager, '_group_list')
    def test_sync_group_db_dont_create_reserved(self, group_list):
        """Populate the list of all TSgroups, ignoring a reserved group name"""
        group_list.return_value = {'allowed': '1', 'reserved': '4'}
        Teamspeak3Manager()._sync_ts_group_db()
        self.assertEqual(TSgroup.objects.all().count(), 1)
        self.assertFalse(TSgroup.objects.filter(ts_group_name='reserved').exists())

    @mock.patch.object(Teamspeak3Manager, '_group_list')
    def test_sync_group_db_delete_reserved(self, group_list):
        """Populate the list of all TSgroups, deleting the TSgroup model for one which has become reserved"""
        TSgroup.objects.create(ts_group_name='reserved', ts_group_id=4)
        group_list.return_value = {'allowed': '1', 'reserved': '4'}
        Teamspeak3Manager()._sync_ts_group_db()
        self.assertEqual(TSgroup.objects.all().count(), 1)
        self.assertFalse(TSgroup.objects.filter(ts_group_name='reserved').exists())

    @mock.patch.object(Teamspeak3Manager, '_group_list')
    def test_sync_group_db_partial_addition(self, group_list):
        """Some TSgroups already exist in database, add new ones"""
        TSgroup.objects.create(ts_group_name='allowed', ts_group_id=1)
        group_list.return_value = {'allowed': '1', 'also allowed': '2'}
        Teamspeak3Manager()._sync_ts_group_db()
        self.assertEqual(TSgroup.objects.all().count(), 2)

    @mock.patch.object(Teamspeak3Manager, '_group_list')
    def test_sync_group_db_partial_removal(self, group_list):
        """One TSgroup has been deleted on server, so remove its model"""
        TSgroup.objects.create(ts_group_name='allowed', ts_group_id=1)
        TSgroup.objects.create(ts_group_name='also allowed', ts_group_id=2)
        group_list.return_value = {'allowed': '1'}
        Teamspeak3Manager()._sync_ts_group_db()
        self.assertEqual(TSgroup.objects.all().count(), 1)


class MockRequest:
    pass


class MockSuperUser:
    def has_perm(self, perm, obj=None):
        return True


request = MockRequest()
request.user = MockSuperUser()


class Teamspeak3AdminTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.group = Group.objects.create(name='test')
        cls.ts_group = TSgroup.objects.create(ts_group_id=1, ts_group_name='test')

    def test_field_queryset_no_reserved_names(self):
        """Ensure all groups are listed when no reserved names"""
        self.assertQuerySetEqual(AuthTSgroupAdmin(AuthTS, AdminSite()).get_form(request).base_fields['auth_group']._get_queryset(), Group.objects.all())
        self.assertQuerySetEqual(AuthTSgroupAdmin(AuthTS, AdminSite()).get_form(request).base_fields['ts_group']._get_queryset(), TSgroup.objects.all())

    def test_field_queryset_reserved_names(self):
        """Ensure reserved group names are filtered out"""
        ReservedGroupName.objects.bulk_create([ReservedGroupName(name='test', reason='tests', created_by='Bob')])
        self.assertQuerySetEqual(AuthTSgroupAdmin(AuthTS, AdminSite()).get_form(request).base_fields['auth_group']._get_queryset(), Group.objects.none())
        self.assertQuerySetEqual(AuthTSgroupAdmin(AuthTS, AdminSite()).get_form(request).base_fields['ts_group']._get_queryset(), TSgroup.objects.none())
