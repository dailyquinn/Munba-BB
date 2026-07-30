import random
import string
import calendar
import datetime as dt
import hashlib
import logging
import re
from typing import Tuple

from packaging import version

from django.db import connections
from django.conf import settings
from django.contrib.auth.models import User

from allianceauth.eveonline.models import EveCharacter

logger = logging.getLogger(__name__)


TABLE_PREFIX = getattr(settings, 'SMF_TABLE_PREFIX', 'smf_')


class SmfManager:
    def __init__(self):
        pass

    # For SMF < 2.1
    SQL_ADD_USER_SMF_20 = r"INSERT INTO %smembers (member_name, passwd, email_address, date_registered, real_name," \
                            r" buddy_list, message_labels, openid_uri, signature, ignore_boards) " \
                            r"VALUES (%%s, %%s, %%s, %%s, %%s, 0, 0, 0, 0, 0)" % TABLE_PREFIX

    # For SMF >= 2.1
    SQL_ADD_USER_SMF_21 = r"INSERT INTO %smembers (member_name, passwd, email_address, date_registered, real_name," \
                            r" buddy_list, signature, ignore_boards) " \
                            r"VALUES (%%s, %%s, %%s, %%s, %%s, 0, 0, 0)" % TABLE_PREFIX

    # returns something like »window.smfVersion = "SMF 2.0.19";«
    SQL_GET_CURRENT_SMF_VERSION = r"SELECT data FROM %sadmin_info_files WHERE filename = %%s" % TABLE_PREFIX

    SQL_DEL_USER = r"DELETE FROM %smembers where member_name = %%s" % TABLE_PREFIX

    SQL_UPD_USER = r"UPDATE %smembers SET email_address = %%s, passwd = %%s, real_name = %%s WHERE member_name = %%s" % TABLE_PREFIX

    SQL_UPD_DISPLAY_NAME = r"UPDATE %smembers SET real_name = %%s WHERE member_name = %%s" % TABLE_PREFIX

    SQL_DIS_USER = r"UPDATE %smembers SET email_address = %%s, passwd = %%s WHERE member_name = %%s" % TABLE_PREFIX

    SQL_USER_ID_FROM_USERNAME = r"SELECT id_member from %smembers WHERE member_name = %%s" % TABLE_PREFIX

    SQL_ADD_USER_GROUP = r"UPDATE %smembers SET additional_groups = %%s WHERE id_member = %%s" % TABLE_PREFIX

    SQL_GET_GROUP_ID = r"SELECT id_group from %smembergroups WHERE group_name = %%s" % TABLE_PREFIX

    SQL_ADD_GROUP = r"INSERT INTO %smembergroups (group_name,description) VALUES (%%s,%%s)" % TABLE_PREFIX

    SQL_UPDATE_USER_PASSWORD = r"UPDATE %smembers SET passwd = %%s WHERE member_name = %%s" % TABLE_PREFIX

    SQL_REMOVE_USER_GROUP = r"UPDATE %smembers SET additional_groups = %%s WHERE id_member = %%s" % TABLE_PREFIX

    SQL_GET_ALL_GROUPS = r"SELECT id_group, group_name FROM %smembergroups" % TABLE_PREFIX

    SQL_GET_USER_GROUPS = r"SELECT additional_groups FROM %smembers WHERE id_member = %%s" % TABLE_PREFIX

    SQL_ADD_USER_AVATAR = r"UPDATE %smembers SET avatar = %%s WHERE id_member = %%s" % TABLE_PREFIX

    @classmethod
    def _get_current_smf_version(cls) -> str:
        """
        Get the current SMF version from the DB
        :return:
        """

        cursor = connections['smf'].cursor()
        cursor.execute(cls.SQL_GET_CURRENT_SMF_VERSION, ['current-version.js'])
        row = cursor.fetchone()
        db_result = row[0]

        pattern = re.compile(r"\d+(\.\d+)+")
        result = pattern.search(db_result)

        smf_version = result.group(0)

        return smf_version


    @staticmethod
    def _sanitize_groupname(name):
        name = name.strip(' _')
        return re.sub(r'[^\w.-]', '', name)

    @staticmethod
    def generate_random_pass():
        return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(16)])

    @staticmethod
    def gen_hash(username_clean, passwd):
        return hashlib.sha1((username_clean + passwd).encode('utf-8')).hexdigest()

    @staticmethod
    def santatize_username(username):
        sanatized = username.replace(" ", "_")
        sanatized = sanatized.replace("'", "_")
        return sanatized.lower()

    @staticmethod
    def get_current_utc_date():
        d = dt.datetime.now(dt.timezone.utc)
        unixtime = calendar.timegm(d.utctimetuple())
        return unixtime

    @classmethod
    def create_group(cls, groupname):
        logger.debug(f"Creating smf group {groupname}")
        cursor = connections['smf'].cursor()
        cursor.execute(cls.SQL_ADD_GROUP, [groupname, groupname])
        logger.info(f"Created smf group {groupname}")
        return cls.get_group_id(groupname)

    @classmethod
    def get_group_id(cls, groupname):
        logger.debug(f"Getting smf group id for groupname {groupname}")
        cursor = connections['smf'].cursor()
        cursor.execute(cls.SQL_GET_GROUP_ID, [groupname])
        row = cursor.fetchone()
        logger.debug(f"Got smf group id {row[0]} for groupname {groupname}")
        return row[0]

    @classmethod
    def check_user(cls, username):
        logger.debug(f"Checking smf username {username}")
        cursor = connections['smf'].cursor()
        cursor.execute(cls.SQL_USER_ID_FROM_USERNAME, [cls.santatize_username(username)])
        row = cursor.fetchone()
        if row:
            logger.debug(f"Found user {username} on smf")
            return True
        logger.debug(f"User {username} not found on smf")
        return False

    @classmethod
    def add_avatar(cls, member_name, characterid):
        logger.debug(f"Adding EVE character id {characterid} portrait as smf avatar for user {member_name}")
        avatar_url = EveCharacter.generic_portrait_url(characterid, 64)
        cursor = connections['smf'].cursor()
        id_member = cls.get_user_id(member_name)
        cursor.execute(cls.SQL_ADD_USER_AVATAR, [avatar_url, id_member])

    @classmethod
    def get_user_id(cls, username):
        logger.debug(f"Getting smf user id for username {username}")
        cursor = connections['smf'].cursor()
        cursor.execute(cls.SQL_USER_ID_FROM_USERNAME, [username])
        row = cursor.fetchone()
        if row is not None:
            logger.debug(f"Got smf user id {row[0]} for username {username}")
            return row[0]
        else:
            logger.error(f"username {username} not found on smf. Unable to determine user id .")
            return None

    @classmethod
    def get_all_groups(cls):
        logger.debug("Getting all smf groups.")
        cursor = connections['smf'].cursor()
        cursor.execute(cls.SQL_GET_ALL_GROUPS)
        rows = cursor.fetchall()
        out = {}
        for row in rows:
            out[row[1]] = row[0]
        logger.debug(f"Got smf groups {out}")
        return out

    @classmethod
    def get_user_groups(cls, userid):
        logger.debug(f"Getting smf user id {userid} groups")
        cursor = connections['smf'].cursor()
        cursor.execute(cls.SQL_GET_USER_GROUPS, [userid])
        out = [row[0] for row in cursor.fetchall()]
        logger.debug(f"Got user {userid} smf groups {out}")
        return out

    @classmethod
    def add_user(cls, username, email_address, groups, main_character: EveCharacter) -> Tuple:
        """
        Add a user to SMF
        :param username:
        :param email_address:
        :param groups:
        :param main_character:
        :return:
        """

        main_character_id = main_character.character_id
        main_character_name = main_character.character_name

        logger.debug(
            f"Adding smf user with member_name: {username}, "
            f"email_address: {email_address}, "
            f"characterid: {main_character_id}, "
            f"main character: {main_character_name}"
        )

        cursor = connections['smf'].cursor()
        username_clean = cls.santatize_username(username)
        passwd = cls.generate_random_pass()
        pwhash = cls.gen_hash(username_clean, passwd)
        register_date = cls.get_current_utc_date()

        logger.debug(f"Proceeding to add smf user {username} and pwhash starting with {pwhash[0:5]}")

        # check if the username was simply revoked
        if cls.check_user(username) is True:
            logger.warning(
                f"Unable to add smf user with username {username} - "
                f"already exists. Updating user instead."
            )

            cls.__update_user_info(
                username_clean, email_address, pwhash, main_character_name
            )
        else:
            try:
                smf_version = cls._get_current_smf_version()
                sql_add_user_arguments = [
                    username_clean,
                    pwhash,
                    email_address,
                    register_date,
                    main_character_name,
                ]

                if version.parse(smf_version) < version.parse("2.1"):
                    logger.debug("SMF compatibility: < 2.1")

                    cursor.execute(cls.SQL_ADD_USER_SMF_20, sql_add_user_arguments)
                else:
                    logger.debug("SMF compatibility: >= 2.1")

                    cursor.execute(cls.SQL_ADD_USER_SMF_21, sql_add_user_arguments)

                cls.add_avatar(username_clean, main_character_id)
                logger.info(f"Added smf member_name {username_clean}")
                cls.update_groups(username_clean, groups)
            except Exception as e:
                logger.warning(f"Unable to add smf user {username_clean}: {e}")
                pass

        return username_clean, passwd

    @classmethod
    def __update_user_info(cls, username, email_address, passwd, main_character_name):
        logger.debug(
            f"Updating smf user {username} info: "
            f"username {email_address} "
            f"password of length {len(passwd)}"
        )
        cursor = connections['smf'].cursor()
        try:
            cursor.execute(
                cls.SQL_UPD_USER, [email_address, passwd, main_character_name, username]
            )
            logger.info(f"Updated smf user {username} info")
        except Exception as e:
            logger.exception(f"Unable to update smf user {username} info. ({e})")
            pass

    @classmethod
    def delete_user(cls, username):
        logger.debug(f"Deleting smf user {username}")
        cursor = connections['smf'].cursor()

        if cls.check_user(username):
            cursor.execute(cls.SQL_DEL_USER, [username])
            logger.info(f"Deleted smf user {username}")
            return True
        logger.error(f"Unable to delete smf user {username} - user not found on smf.")
        return False

    @classmethod
    def update_display_name(cls, user: User):
        logger.debug(f"Updating SMF displayed name for user {user}")
        cursor = connections['smf'].cursor()
        smf_username = user.smf.username

        try:
            display_name = user.profile.main_character.character_name
        except Exception as exc:
            logger.exception(
                f"Unable to find a main character name for {user}, skipping... ({exc})"
            )
            display_name = smf_username

        if cls.check_user(smf_username):
            cursor.execute(cls.SQL_UPD_DISPLAY_NAME, [display_name, smf_username])
            logger.info(f"Updated displayed name for smf user {smf_username}")
            return True
        logger.error(f"Unable to update smf user {smf_username} - user not found on smf.")
        return False

    @classmethod
    def update_groups(cls, username, groups):
        userid = cls.get_user_id(username)
        logger.debug(f"Updating smf user {username} with id {userid} groups {groups}")
        if userid is not None:
            forum_groups = cls.get_all_groups()
            user_groups = set(cls.get_user_groups(userid))
            act_groups = {cls._sanitize_groupname(g) for g in groups}
            addgroups = act_groups - user_groups
            remgroups = user_groups - act_groups
            logger.info(f"Updating smf user {username} groups - adding {addgroups}, removing {remgroups}")
            act_group_id = set()
            for g in addgroups:
                if g not in forum_groups:
                    forum_groups[g] = cls.create_group(g)
                act_group_id.add(str(cls.get_group_id(g)))
            string_groups = ','.join(act_group_id)
            cls.add_user_to_group(userid, string_groups)

    @classmethod
    def add_user_to_group(cls, userid, groupid):
        logger.debug(f"Adding smf user id {userid} to group id {groupid}")
        try:
            cursor = connections['smf'].cursor()
            cursor.execute(cls.SQL_ADD_USER_GROUP, [groupid, userid])
            logger.info(f"Added smf user id {userid} to group id {groupid}")
        except Exception as e:
            logger.exception(f"Unable to add smf user id {userid} to group id {groupid} ({e})")
            pass

    @classmethod
    def remove_user_from_group(cls, userid, groupid):
        logger.debug(f"Removing smf user id {userid} from group id {groupid}")
        try:
            cursor = connections['smf'].cursor()
            cursor.execute(cls.SQL_REMOVE_USER_GROUP, [groupid, userid])
            logger.info(f"Removed smf user id {userid} from group id {groupid}")
        except Exception as e:
            logger.exception(f"Unable to remove smf user id {userid} from group id {groupid} ({e})")
            pass

    @classmethod
    def disable_user(cls, username):
        logger.debug(f"Disabling smf user {username}")
        cursor = connections['smf'].cursor()

        password = cls.generate_random_pass()
        revoke_email = "revoked@localhost"
        try:
            pwhash = cls.gen_hash(username, password)
            cursor.execute(cls.SQL_DIS_USER, [revoke_email, pwhash, username])
            cls.get_user_id(username)
            cls.update_groups(username, [])
            logger.info(f"Disabled smf user {username}")
            return True
        except TypeError:
            logger.exception(f"TypeError occured while disabling user {username} - failed to disable.")
            return False

    @classmethod
    def update_user_password(cls, username, characterid, password=None):
        logger.debug(f"Updating smf user {username} password")
        cursor = connections['smf'].cursor()
        if not password:
            password = cls.generate_random_pass()
        if cls.check_user(username):
            username_clean = cls.santatize_username(username)
            pwhash = cls.gen_hash(username_clean, password)
            logger.debug(
                f"Proceeding to update smf user {username} "
                f"password with pwhash starting with {pwhash[0:5]}"
            )
            cursor.execute(cls.SQL_UPDATE_USER_PASSWORD, [pwhash, username])
            cls.add_avatar(username, characterid)
            logger.info(f"Updated smf user {username} password.")
            return password
        logger.error(f"Unable to update smf user {username} password - user not found on smf.")
        return ""
