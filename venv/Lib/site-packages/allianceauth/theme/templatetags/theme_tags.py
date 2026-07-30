from django import template
from django.conf import settings

from allianceauth.hooks import get_hooks

register = template.Library()


def hook_to_name(th):
    return f"{th.__class__.__module__}.{th.__class__.__name__}"


def get_theme_from_hooks(theme, hooks):
    for h in hooks:
        _h = h()
        _hn = hook_to_name(_h)
        if _hn == theme:
            return _h


def get_theme(request):
    theme = settings.DEFAULT_THEME
    hooks = get_hooks('theme_hook')

    try:
        theme = request.session.get('THEME', settings.DEFAULT_THEME_DARK if request.session.get('NIGHT_MODE', False) is True else settings.DEFAULT_THEME)
    except AttributeError:
        pass

    theme_hook = get_theme_from_hooks(theme, hooks)

    if not theme_hook:
        theme_hook = get_theme_from_hooks(settings.DEFAULT_THEME, hooks)

    return theme_hook


def get_theme_context(request):
    return {
        'theme': get_theme(request),
        'request': request
    }


@register.inclusion_tag('theme/theme_imports_css.html', takes_context=True)
def theme_css(context):
    request = context['request']
    return get_theme_context(request)


@register.simple_tag(takes_context=True)
def theme_html_tags(context):
    request = context['request']
    theme = get_theme(request)
    return getattr(theme, "html_tags", "")


@register.simple_tag(takes_context=True)
def header_padding_size(context):
    request = context['request']
    theme = get_theme(request)
    return getattr(theme, "header_padding")


@register.inclusion_tag('theme/theme_imports_js.html', takes_context=True)
def theme_js(context):
    request = context['request']
    return get_theme_context(request)


@register.inclusion_tag('theme/theme_select.html', takes_context=True)
def theme_select(context):
    request = context['request']
    return {
        'next': request.path,
        'themes': get_hooks('theme_hook'),
        'selected_theme': get_theme(request)
    }
