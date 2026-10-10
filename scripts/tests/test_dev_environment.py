import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IndependentEnvironment(unittest.TestCase):
    def test_start_guards_effective_compose_and_uses_disposable_operations(self):
        setup, env = load("setup_dev"), load("dev_environment")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = setup.create_config(root, "alice", 14231)
            with patch.object(env, "ROOT", root):
                _, values = env.configuration(path)
                effective = {
                    "name": values["COMPOSE_PROJECT_NAME"],
                    "volumes": {
                        "postgres_data": {
                            "name": values["COMPOSE_PROJECT_NAME"] + "_postgres_data"
                        }
                    },
                    "services": {
                        "backend": {
                            "image": values["COMPOSE_PROJECT_NAME"] + "-backend",
                            "environment": values,
                        },
                        "postgres": {"environment": values},
                    },
                }
                import json

                with (
                    patch.object(env, "provenance"),
                    patch.object(
                        env, "execute", return_value=json.dumps(effective)
                    ) as execute,
                ):
                    env.run(path, "start")
                    operation = next(
                        call.args[0]
                        for call in execute.call_args_list
                        if "run" in call.args[0]
                    )
                    self.assertIn("--rm", operation)
                    compile(operation[-1], "<guard>", "exec")
                    self.assertIn("current_database()", operation[-1])
                    self.assertIn("get_current_head()", operation[-1])
                with (
                    patch.object(env, "provenance"),
                    patch.object(
                        env, "execute", return_value=json.dumps(effective)
                    ) as execute,
                ):
                    env.run(path, "initialize")
                    commands = [call.args[0] for call in execute.call_args_list]
                    first_run = next(
                        index
                        for index, command in enumerate(commands)
                        if "run" in command
                    )
                    first_stop = next(
                        index
                        for index, command in enumerate(commands)
                        if "stop" in command
                    )
                    self.assertLess(first_run, first_stop)
                    self.assertIn("to_regclass", commands[first_run][-1])
                    for command in commands:
                        if "run" in command:
                            compile(command[-1], "<initialization guard>", "exec")
                effective["name"] = "foreign"
                with (
                    patch.object(env, "provenance"),
                    patch.object(
                        env, "execute", return_value=json.dumps(effective)
                    ) as execute,
                ):
                    with self.assertRaises(ValueError):
                        env.run(path, "start")
                    self.assertEqual(execute.call_count, 1)

    def test_private_configs_are_independent_and_never_overwritten(self):
        setup = load("setup_dev")
        env = load("dev_environment")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = setup.create_config(root, "alice", 14231)
            second = setup.create_config(root, "bob", 14232)
            with patch.object(env, "ROOT", root):
                _, a = env.configuration(first)
                _, b = env.configuration(second)
                self.assertNotEqual(a["POSTGRES_DB"], b["POSTGRES_DB"])
                self.assertNotEqual(a["POSTGRES_PASSWORD"], b["POSTGRES_PASSWORD"])
                self.assertNotEqual(
                    a["COMPOSE_PROJECT_NAME"], b["COMPOSE_PROJECT_NAME"]
                )
                with self.assertRaises(FileExistsError):
                    setup.create_config(root, "alice", 14231)
                first.write_text(first.read_text().replace(a["POSTGRES_DB"], "paideia"))
                with self.assertRaises(ValueError):
                    env.configuration(first)

    def test_refuses_unproven_volume_before_any_mutation(self):
        env = load("dev_environment")
        with patch.object(
            env,
            "execute",
            side_effect=["", "paideia-dev-alice_postgres_data", '[{"Labels": {}}]'],
        ) as execute:
            with self.assertRaises(ValueError):
                env.provenance("paideia-dev-alice")
            self.assertTrue(
                all(
                    call.args[0][1] in {"ps", "volume"}
                    for call in execute.call_args_list
                )
            )


if __name__ == "__main__":
    unittest.main()
