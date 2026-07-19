import unittest
from dataclasses import replace

from backend.config import get_settings
from backend.production import production_configuration_report


class ProductionSafetyTest(unittest.TestCase):
    def test_unsafe_production_defaults_are_blocked(self) -> None:
        settings = replace(get_settings(), app_env="production", auth_secret_key="dev-only-change-this-secret", openai_api_key=None, database_url="sqlite:///tmp.db")
        report = production_configuration_report(settings)
        self.assertFalse(report["passed"])
        self.assertGreaterEqual(len(report["errors"]), 3)

    def test_safe_production_shape_passes(self) -> None:
        settings = replace(get_settings(), app_env="production", auth_secret_key="x" * 40, openai_api_key="configured", database_url="postgresql://host/db")
        self.assertTrue(production_configuration_report(settings)["passed"])


if __name__ == "__main__": unittest.main()
