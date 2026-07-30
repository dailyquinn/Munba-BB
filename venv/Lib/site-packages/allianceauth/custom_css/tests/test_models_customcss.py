from django.test import TestCase

from allianceauth.custom_css.models import CustomCSS


class TestCompressCSS(TestCase):
    """
    Test cases for the compress_css method of the CustomCSS model
    """

    def test_compresses_css_by_removing_comments(self):
        """
        Test that the compress_css method removes CSS comments

        :return:
        :rtype:
        """

        instance = CustomCSS(css="body { color: red; } /* This is a comment */")
        compressed = instance.compress_css()

        self.assertNotIn("/* This is a comment */", compressed)

    def test_compresses_css_by_removing_extra_spaces(self):
        """
        Test that the compress_css method removes extra spaces

        :return:
        :rtype:
        """

        instance = CustomCSS(css="body    {    color:    red;    }")
        compressed = instance.compress_css()

        self.assertEqual(compressed, "body{color:red}")

    def test_compresses_css_by_shortening_hex_colors(self):
        """
        Test that the compress_css method shortens hex colors when possible

        :return:
        :rtype:
        """

        instance = CustomCSS(css="body { color: #aabbcc; }")
        compressed = instance.compress_css()

        self.assertIn("#abc", compressed)

    def test_retains_url_without_quotes(self):
        """
        Test that the compress_css method retains url() values without quotes

        :return:
        :rtype:
        """

        instance = CustomCSS(css="body { background: url('image.png'); }")
        compressed = instance.compress_css()

        self.assertIn("url(image.png)", compressed)

    def test_handles_empty_css_gracefully(self):
        """
        Test that the compress_css method handles empty CSS gracefully

        :return:
        :rtype:
        """

        instance = CustomCSS(css="")
        compressed = instance.compress_css()

        self.assertEqual(compressed, "")

    def test_handles_invalid_css_gracefully(self):
        """
        Test that the compress_css method handles invalid CSS gracefully

        :return:
        :rtype:
        """

        instance = CustomCSS(css="invalid-css")
        compressed = instance.compress_css()

        self.assertEqual(compressed, "")


class TestSave(TestCase):
    """
    Test cases for the save method of the CustomCSS model
    """

    def test_saves_instance_with_compressed_css(self):
        """
        Test that the save method saves the instance with compressed CSS

        :return:
        :rtype:
        """

        instance = CustomCSS(css="body { color: red; } /* comment */")
        instance.save()

        self.assertEqual(instance.css_compressed, "body{color:red}")

    def test_overwrites_primary_key_on_save(self):
        """
        Test that the save method overwrites the primary key to 1

        :return:
        :rtype:
        """

        instance = CustomCSS(css="body { color: red; }")
        instance.save()

        self.assertEqual(instance.pk, 1)

    def test_handles_save_with_empty_css(self):
        """
        Test that the save method handles saving an instance with empty CSS

        :return:
        :rtype:
        """

        instance = CustomCSS(css="")
        instance.save()

        self.assertEqual(instance.css_compressed, "")

    def test_retains_existing_compressed_css_on_save(self):
        """
        Test that the save method retains existing compressed CSS if the css field is not changed

        :return:
        :rtype:
        """

        instance = CustomCSS(css="body { color: blue; }")
        instance.css_compressed = "body{color:blue}"
        instance.save()

        self.assertEqual(instance.css_compressed, "body{color:blue}")


class TestModelNameAndfields(TestCase):
    """
    Test cases for the model name and fields of the CustomCSS model
    """

    def test_model_name(self):
        """
        Test that the model name is correct

        :return:
        :rtype:
        """

        instance = CustomCSS()
        self.assertEqual(str(instance), "Custom CSS")

    def test_fields(self):
        """
        Test that the model fields are correct

        :return:
        :rtype:
        """

        instance = CustomCSS()
        self.assertTrue(hasattr(instance, "css"))
        self.assertTrue(hasattr(instance, "css_compressed"))
        self.assertTrue(hasattr(instance, "timestamp"))

    def test_allows_null_and_blank_values_for_css_fields(self):
        """
        Test that the css and css_compressed fields allow null and blank values

        :return:
        :rtype:
        """

        instance = CustomCSS(css=None, css_compressed=None)
        instance.full_clean()  # Should not raise ValidationError

    def test_updates_timestamp_on_save(self):
        """
        Test that the timestamp field is updated on save

        :return:
        :rtype:
        """

        instance = CustomCSS(css="body { color: red; }")
        instance.save()

        previous_timestamp = instance.timestamp

        instance.css = "body { color: blue; }"
        instance.save()

        self.assertNotEqual(instance.timestamp, previous_timestamp)
