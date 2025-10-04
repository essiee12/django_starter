from django.test import TestCase

from base.tests.factories import ConfigFactory


class ConfigModelTests(TestCase):
    def test_str_returns_name(self):
        config = ConfigFactory.create(name="Feature Toggle")
        self.assertEqual(str(config), "Feature Toggle")

    def test_updated_at_changes_on_save(self):
        config = ConfigFactory.create(value="initial")
        first_updated_at = config.updated_at

        config.value = "updated"
        config.save()
        config.refresh_from_db()

        self.assertGreater(config.updated_at, first_updated_at)
