import tempfile
import webbrowser
from pathlib import Path

from bs4 import BeautifulSoup

from django.http import HttpResponse
from django.template import Context, Template

PACKAGE_PATH = "allianceauth.menu"


def extract_links(response: HttpResponse) -> dict:
    soup = extract_html(response)
    links = {
        link["href"]: "".join(link.stripped_strings)
        for link in soup.find_all("a", href=True)
    }
    return links


def extract_html(response: HttpResponse) -> BeautifulSoup:
    soup = BeautifulSoup(response.content, "html.parser")
    return soup


def open_page_in_browser(response: HttpResponse):
    """Open the response in the system's default browser.

    This will create a temporary file in the user's home.
    """
    path = Path.home() / "temp"
    path.mkdir(exist_ok=True)

    with tempfile.NamedTemporaryFile(dir=path, delete=False) as file:
        file.write(response.content)
        webbrowser.open(file.name)


def render_template(string, context=None):
    context = context or {}
    context = Context(context)
    return Template(string).render(context)


def remove_whitespaces(s) -> str:
    return s.replace("\n", "").strip()
