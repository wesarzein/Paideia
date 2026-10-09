import tempfile
import unittest
from pathlib import Path

from setup_dev import create_config


class BootstrapTests(unittest.TestCase):
    def test_existing_configuration_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = create_config(root, "developer-a", 14200)
            original = destination.read_bytes()
            with self.assertRaises(FileExistsError):
                create_config(root, "developer-a", 14201)
            self.assertEqual(destination.read_bytes(), original)

    def test_two_environments_have_independent_credentials_and_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a = create_config(root, "developer-a", 14200).read_text(encoding="utf-8")
            b = create_config(root, "developer-b", 14201).read_text(encoding="utf-8")
            av = dict(line.split("=", 1) for line in a.splitlines())
            bv = dict(line.split("=", 1) for line in b.splitlines())
            for key in (
                "COMPOSE_PROJECT_NAME", "POSTGRES_DB", "POSTGRES_PASSWORD", "JWT_SECRET_KEY"
            ):
                self.assertNotEqual(av[key], bv[key])
            self.assertTrue(av["POSTGRES_DB"].startswith("paideia_dev_"))

    def test_invalid_name_cannot_escape_configuration_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                create_config(Path(directory), "../outside", 14200)

    def test_default_legacy_ports_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                create_config(Path(directory), "developer", 4200)


if __name__ == "__main__":
    unittest.main()
