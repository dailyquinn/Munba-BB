from django.test import TestCase

from allianceauth.srp.form import SrpFleetUserRequestForm


class TestForms(TestCase):

    def test_allow_missing_trailing_slash_zkillboard(self):
        form = SrpFleetUserRequestForm(
            data = {
                "killboard_link": "https://zkillboard.com/kill/130429493",
                "additional_info": "Details",
            }
        )
        form.cleaned_data = {"killboard_link": "https://zkillboard.com/kill/130429493"}

        self.assertEqual("https://zkillboard.com/kill/130429493/", form.clean_killboard_link())

    def test_not_add_trailling_slash_kb_evetools(self):
        form = SrpFleetUserRequestForm(
            data = {
                "killboard_link": "https://kb.evetools.org/kill/130429493",
            }
        )
        form.cleaned_data = {"killboard_link": "https://kb.evetools.org/kill/130429493"}

        self.assertEqual("https://kb.evetools.org/kill/130429493", form.clean_killboard_link())
