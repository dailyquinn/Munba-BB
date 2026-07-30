from itertools import count

from django.contrib.auth.models import User

from allianceauth.menu.core import menu_item_hooks
from allianceauth.menu.models import MenuItem
from allianceauth.menu.templatetags.menu_menu_items import RenderedMenuItem
from allianceauth.services.auth_hooks import MenuItemHook
from allianceauth.tests.auth_utils import AuthUtils


def create_user(permissions=None, **kwargs) -> User:
    num = next(counter_user)
    params = {"username": f"test_user_{num}"}
    params.update(kwargs)
    user = User.objects.create(**params)
    if permissions:
        user = AuthUtils.add_permissions_to_user_by_name(perms=permissions, user=user)
    return user


def create_menu_item_hook_class(**kwargs) -> MenuItemHook:
    num = next(counter_menu_item_hook)
    return type(f"GeneratedMenuItem{num}", (MenuItemHook,), {})


def create_menu_item_hook(**kwargs) -> MenuItemHook:
    num = next(counter_menu_item_hook)
    new_class = type(f"GeneratedMenuItem{num}", (MenuItemHook,), {})

    count = kwargs.pop("count", None)
    params = {
        "text": f"Dummy App #{num}",
        "classes": "fa-solid fa-users-gear",
        "url_name": "groupmanagement:management",
    }
    params.update(kwargs)
    obj = new_class(**params)
    for key, value in params.items():
        setattr(obj, key, value)

    obj.count = count
    return obj


def create_menu_item_hook_function(**kwargs):
    obj = create_menu_item_hook(**kwargs)
    return lambda: obj


def create_link_menu_item(**kwargs) -> MenuItem:
    num = next(counter_menu_item)
    params = {
        "url": f"https://www.example.com/{num}",
    }
    params.update(kwargs)
    return _create_menu_item(**params)


def create_app_menu_item(**kwargs) -> MenuItem:
    params = {"hook_hash": "hook_hash"}
    params.update(kwargs)
    return _create_menu_item(**params)


def create_folder_menu_item(**kwargs) -> MenuItem:
    return _create_menu_item(**kwargs)


def create_menu_item_from_hook(hook, **kwargs) -> MenuItem:
    item = hook()
    hook_params = menu_item_hooks.gather_params(item)
    params = {
        "text": hook_params.text,
        "hook_hash": hook_params.hash,
        "order": hook_params.order,
    }
    params.update(kwargs)
    return _create_menu_item(**params)


def _create_menu_item(**kwargs) -> MenuItem:
    num = next(counter_menu_item)
    params = {
        "text": f"text #{num}",
    }
    params.update(kwargs)
    return MenuItem.objects.create(**params)


def create_rendered_menu_item(**kwargs) -> RenderedMenuItem:
    if "menu_item" not in kwargs:
        kwargs["menu_item"] = create_link_menu_item()

    return RenderedMenuItem(**kwargs)


counter_menu_item = count(1, 1)
counter_menu_item_hook = count(1, 1)
counter_user = count(1, 1)
