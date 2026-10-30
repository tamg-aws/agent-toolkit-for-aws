"""Independent advisory, review-package and public-demo tests using synthetic data."""

import copy
import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))

import intake
import knowledge
import preflight
import review_package
import source
import test_continuum_runtime as fixtures
import triage
import workflow
from store import Store, read_json, sha

PLUGIN = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "continuum_public_demo", PLUGIN / "examples" / "overlap-demo" / "demo.py"
)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def advisory(store):
    return {
        "schema_version": "triage-v1",
        "inventory": store.latest("inventory")["object"],
        "author": "synthetic-importer",
        "review": {
            "reviewer": "synthetic-reviewer",
            "verdict": "reviewed",
            "evidence": "Synthetic lossless import review, not a live security review.",
        },
        "findings": [
            {
                "finding_id": key,
                "disposition": "deferred",
                "reason": "No newly selected remediation.",
                "evidence": "Historical synthetic assessment retained.",
                "original_record": {
                    "service_verdict": "FALSE_POSITIVE",
                    "independent_assessment": "supported",
                    "custom_fields": {"unicode": "é", "literal": "$(not-a-command)"},
                },
            }
            for key in store.value("inventory")["findings"]
        ],
        "advisory_groups": [
            {
                "id": "historical-label",
                "finding_ids": list(store.value("inventory")["findings"]),
                "hypothesis": "Shared component, distinct issues remain possible.",
                "evidence": "Synthetic historical records.",
                "uncertainty": "No joint patch, test or source compatibility proof.",
            }
        ],
        "original_document": {"unknown_historical_field": {"preserve": [1, 2, 3]}},
    }


class AdvisoryAccountingTests(fixtures.StateCase):
    def setUp(self):
        super().setUp()
        intake.import_export(self.store, fixtures.export())
        self.value = advisory(self.store)

    def test_lossless_checkpoint_has_no_execution_authority_and_is_idempotent(self):
        first = triage.freeze(self.store, self.value)
        self.assertEqual(self.store.get(first["document"]), self.value)
        self.assertEqual(first["dispositions"], {"deferred": 2})
        self.assertEqual(
            first["authority"], "advisory_only_no_setup_plan_execution_or_publication"
        )
        events = self.store.events()
        self.assertEqual(triage.freeze(self.store, copy.deepcopy(self.value)), first)
        self.assertEqual(self.store.events(), events)
        with self.assertRaisesRegex(ValueError, "No setup"):
            workflow.active(self.store)

    def test_selected_legacy_label_cannot_create_an_execution_plan(self):
        self.value["findings"][0]["disposition"] = "selected-in-old-tool"
        triage.freeze(self.store, self.value)
        self.assertEqual(
            [item["kind"] for item in self.store.events()], ["inventory", "triage"]
        )
        with self.assertRaisesRegex(ValueError, "No setup"):
            review_package.prepare(self.store, str(self.root))

    def test_complete_134_record_fixture_preserves_conflicting_verdicts_and_every_field(
        self,
    ):
        exported = fixtures.export()
        template = exported["findings"][0]
        exported["findings"] = [
            {**template, "findingId": f"finding{number:03d}"} for number in range(134)
        ]
        exported["issues"][0]["findingIds"] = [
            item["findingId"] for item in exported["findings"]
        ]
        intake.import_export(self.store, exported)
        value = advisory(self.store)
        result = triage.freeze(self.store, value)
        _, retained = triage.current(self.store)
        self.assertEqual(result["dispositions"], {"deferred": 134})
        self.assertEqual(retained, value)
        self.assertEqual(len(retained["findings"]), 134)
        self.assertEqual(
            retained["findings"][133]["original_record"]["service_verdict"],
            "FALSE_POSITIVE",
        )
        self.assertEqual(
            retained["findings"][133]["original_record"]["independent_assessment"],
            "supported",
        )

    def test_omitted_duplicate_unknown_and_foreign_inventory_are_rejected(self):
        variants = []
        omitted = copy.deepcopy(self.value)
        omitted["findings"].pop()
        variants.append(omitted)
        repeated = copy.deepcopy(self.value)
        repeated["findings"].append(copy.deepcopy(repeated["findings"][0]))
        variants.append(repeated)
        unknown = copy.deepcopy(self.value)
        unknown["findings"][0]["finding_id"] = "not-in-inventory"
        variants.append(unknown)
        foreign = copy.deepcopy(self.value)
        foreign["inventory"] = "0" * 64
        variants.append(foreign)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                triage.freeze(self.store, value)
        self.assertFalse(
            any(event["kind"] == "triage" for event in self.store.events())
        )

    def test_duplicate_requires_direct_canonical_target_and_cannot_cycle(self):
        self.value["findings"][0].update(
            disposition="duplicate", duplicate_of="finding2"
        )
        triage.freeze(self.store, self.value)
        self.value["findings"][1].update(
            disposition="duplicate", duplicate_of="finding1"
        )
        with self.assertRaisesRegex(ValueError, "direct canonical"):
            triage.freeze(self.store, self.value)
        self.value["findings"][1]["duplicate_of"] = "finding2"
        with self.assertRaisesRegex(ValueError, "direct canonical"):
            triage.freeze(self.store, self.value)

    def test_unknown_advisory_member_and_execution_field_are_rejected(self):
        self.value["advisory_groups"][0]["finding_ids"].append("missing")
        with self.assertRaisesRegex(ValueError, "membership"):
            triage.freeze(self.store, self.value)
        self.value["advisory_groups"][0]["finding_ids"].pop()
        self.value["run"] = {"passed": True}
        with self.assertRaisesRegex(ValueError, "unknown"):
            triage.freeze(self.store, self.value)

    def test_advisory_revision_retains_previous_checkpoint_and_stale_inventory_fails(
        self,
    ):
        first = triage.freeze(self.store, self.value)
        first_key = self.store.latest("triage")["object"]
        self.value["findings"][0]["reason"] = "Updated attributed rationale."
        second = triage.freeze(self.store, self.value)
        self.assertEqual(second["previous"], first_key)
        self.assertEqual(
            self.store.get(first["document"])["findings"][0]["reason"],
            "No newly selected remediation.",
        )
        inventory = copy.deepcopy(self.store.value("inventory"))
        inventory["findings"]["finding1"]["title"] = "Changed service information"
        self.store.append("inventory", inventory)
        with self.assertRaisesRegex(ValueError, "stale"):
            triage.current(self.store)


class SourceMapCase(fixtures.StateCase):
    def setUp(self):
        super().setUp()
        intake.import_export(self.store, fixtures.export())
        self.repo = self.root / "app"
        self.repo.mkdir()
        (self.repo / "app.py").write_bytes(b"def load():\r\n    return 'synthetic'\r\n")
        for args in (
            ("init", "-b", "fixture"),
            ("add", "."),
            (
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-m",
                "Record synthetic source",
            ),
        ):
            source.git(self.repo, *args)
        snapshot = source.snapshot(self.store, str(self.repo))
        raw = (self.repo / "app.py").read_bytes()
        self.value = {
            "schema_version": "knowledge-v1",
            "inventory": self.store.latest("inventory")["object"],
            "revision": snapshot["revision"],
            "author": "synthetic-map-author",
            "citations": [
                {
                    "id": "load-source",
                    "path": "app.py",
                    "start_line": 1,
                    "end_line": 2,
                    "file_sha256": sha(raw),
                    "quote_sha256": sha(raw),
                }
            ],
            "nodes": [
                {
                    "id": "loader",
                    "kind": "component",
                    "label": "Synthetic loader",
                    "citation_ids": ["load-source"],
                }
            ],
            "edges": [
                {
                    "id": "finding-loader",
                    "from": "finding:finding1",
                    "to": "component:loader",
                    "relationship": "affects",
                    "citation_ids": ["load-source"],
                    "assessment": {
                        "reviewer": "synthetic-map-reviewer",
                        "verdict": "unknown",
                        "reason": "Source exists; runtime exploitability has not been checked.",
                    },
                }
            ],
        }

    def freeze(self):
        return knowledge.freeze(self.store, str(self.repo), self.value)


class KnowledgeTests(SourceMapCase):
    def test_exact_crlf_source_links_and_unknown_semantics_remain_distinct(self):
        self.freeze()
        recorded = knowledge.application_map(self.store)
        current = knowledge.application_map(self.store, str(self.repo))
        self.assertEqual(
            recorded["source_freshness"], "recorded_bytes_only_current_tree_unchecked"
        )
        self.assertEqual(current["source_freshness"], "current_bytes_verified")
        edge = next(
            item for item in current["edges"] if item.get("id") == "finding-loader"
        )
        self.assertEqual(edge["assessment"]["verdict"], "unknown")
        self.assertEqual(edge["evidence_class"], "source_anchored_semantic_assertion")
        citation = current["citations"][0]
        self.assertEqual(citation["object_path"], "objects/" + citation["file_sha256"])
        self.assertEqual(
            self.store.raw(citation["file_sha256"]), (self.repo / "app.py").read_bytes()
        )

    def test_wrong_file_span_line_bounds_or_revision_are_rejected(self):
        for field, value in (
            ("file_sha256", "0" * 64),
            ("quote_sha256", "0" * 64),
            ("start_line", 0),
            ("start_line", True),
            ("end_line", 3),
            ("path", "../app.py"),
            ("path", "missing.py"),
        ):
            original = copy.deepcopy(self.value)
            self.value["citations"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.freeze()
            self.value = original
        self.value["revision"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "revision"):
            self.freeze()

    def test_unknown_endpoints_refs_and_self_review_are_rejected(self):
        for mutate in (
            lambda value: value["edges"][0].update(to="component:missing"),
            lambda value: value["edges"][0].update(citation_ids=["missing"]),
            lambda value: value["nodes"][0].update(citation_ids=[]),
            lambda value: value["edges"][0]["assessment"].update(
                reviewer=value["author"]
            ),
            lambda value: value["edges"][0]["assessment"].update(verdict="proven"),
        ):
            original = copy.deepcopy(self.value)
            mutate(self.value)
            with self.assertRaises(ValueError):
                self.freeze()
            self.value = original

    def test_deleted_mutated_or_new_source_invalidates_current_map(self):
        self.freeze()
        original = (self.repo / "app.py").read_bytes()
        for change in ("modify", "delete", "add"):
            with self.subTest(change=change):
                if change == "modify":
                    (self.repo / "app.py").write_bytes(original + b"# changed\n")
                elif change == "delete":
                    (self.repo / "app.py").unlink()
                    (self.repo / "other.py").write_text("value = 1\n")
                else:
                    (self.repo / "other.py").write_text("value = 1\n")
                with self.assertRaisesRegex(ValueError, "stale"):
                    knowledge.application_map(self.store, str(self.repo))
                self.assertEqual(
                    knowledge.application_map(self.store)["source_freshness"],
                    "recorded_bytes_only_current_tree_unchecked",
                )
                (self.repo / "app.py").write_bytes(original)
                (self.repo / "other.py").unlink(missing_ok=True)

    def test_same_document_refresh_after_triage_change_records_new_context(self):
        first = self.freeze()
        first_key = self.store.latest("knowledge")["object"]
        triage.freeze(self.store, advisory(self.store))
        with self.assertRaisesRegex(ValueError, "stale"):
            knowledge.application_map(self.store)
        second = self.freeze()
        self.assertEqual(second["document"], first["document"])
        self.assertEqual(second["previous"], first_key)
        self.assertNotEqual(second["triage"], first["triage"])
        events = self.store.events()
        self.assertEqual(self.freeze(), second)
        self.assertEqual(self.store.events(), events)
        knowledge.application_map(self.store, str(self.repo))

    def test_changed_inventory_rejects_old_knowledge(self):
        self.freeze()
        inventory = copy.deepcopy(self.store.value("inventory"))
        inventory["findings"]["finding1"]["title"] = "New finding details"
        self.store.append("inventory", inventory)
        with self.assertRaisesRegex(ValueError, "stale"):
            knowledge.application_map(self.store)
        with self.assertRaisesRegex(ValueError, "inventory"):
            self.freeze()

    def test_markdown_does_not_activate_untrusted_labels_or_links(self):
        malicious = "[click](https://invalid.example) <img src=x onerror=alert(1)>"
        self.value["nodes"][0]["label"] = malicious
        self.value["edges"][0]["assessment"]["reason"] = malicious
        self.freeze()
        rendered = knowledge.markdown(knowledge.application_map(self.store))
        self.assertNotIn(malicious, rendered)
        self.assertNotIn("<img", rendered)
        self.assertNotIn("](https:", rendered)
        self.assertIn("unknown", rendered)
        self.assertIn(
            "(objects/" + self.value["citations"][0]["file_sha256"] + ")", rendered
        )


class ReviewPackageTests(unittest.TestCase):
    def setUp(self):
        self.case = fixtures.SourceAndWorkflowTests()
        self.case.setUp()

    def tearDown(self):
        self.case.tearDown()

    def ready(self):
        self.case.make_synthetic_reviewed_candidate()
        source.git(self.case.repo, "reset", "--soft", self.case.revision)

    def prepare(self):
        return review_package.prepare(self.case.store, str(self.case.repo))

    def test_local_package_preserves_whole_accounting_and_fixed_check_proofs(self):
        self.ready()
        result = self.prepare()
        self.assertEqual(result["status"], "LOCAL_REVIEW_ONLY")
        self.assertEqual(
            result["counts"],
            {"findings": 2, "service_issues": 1, "local_issues": 2, "fix_groups": 2},
        )
        self.assertEqual(result["accounting"], self.case.plan["findings"])
        self.assertEqual(result["dependency_batches"], [["group-a", "group-b"]])
        self.assertEqual(len(result["checks"]), len(self.case.app["checks"]))
        self.assertEqual(result["changed_paths"], ["app.py"])
        self.assertIn(b"-value = 1", self.case.store.raw(result["diff_sha256"]))
        self.assertIn(
            "not automated semantic analysis", " ".join(result["limitations"])
        )
        rendered = review_package.markdown(result)
        self.assertIn("LOCAL REVIEW ONLY", rendered)
        self.assertIn("finding1", rendered)
        self.assertEqual(
            self.case.store.latest("review_package")["object"],
            self.case.store.save(result),
        )

    def test_later_commit_invalidates_exact_revision_review_package(self):
        self.case.make_synthetic_reviewed_candidate()
        with self.assertRaisesRegex(ValueError, "revision differs"):
            self.prepare()

    def test_stale_source_or_plan_cannot_export_prior_green(self):
        self.ready()
        (self.case.repo / "app.py").write_text("value = 3\n")
        with self.assertRaisesRegex(ValueError, "differs"):
            self.prepare()
        (self.case.repo / "app.py").write_text("value = 2\n")
        changed = copy.deepcopy(self.case.plan)
        changed["groups"][0]["rationale"] = "Changed reviewed scope"
        workflow.freeze_plan(self.case.store, changed)
        with self.assertRaisesRegex(ValueError, "stale"):
            self.prepare()

    def test_unresolved_later_intent_blocks_export_of_previous_pass(self):
        self.ready()
        self.case.store.append("run_intent", {"id": "interrupted"})
        self.case.store.append(
            "run_error",
            {"intent": {"id": "interrupted"}, "error": "Synthetic interruption"},
        )
        with self.assertRaisesRegex(ValueError, "stale|unresolved"):
            self.prepare()

    def test_new_failed_execution_blocks_export_of_previous_pass(self):
        self.ready()
        record = copy.deepcopy(self.case.store.value("run"))
        record.update(intent="new-attempt", passed=False)
        self.case.store.append("run_intent", {"id": "new-attempt"})
        self.case.store.append("run", record)
        with self.assertRaisesRegex(ValueError, "stale|unresolved"):
            self.prepare()

    def test_tampered_check_log_or_claimed_success_cannot_export(self):
        self.ready()
        record = self.case.store.value("run")
        (self.case.store.root / "objects" / record["checks"][0]["stdout"]).write_bytes(
            b"tampered"
        )
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.prepare()

    def append_failed_drift_then_clean_pass(self, claimed_pass=False):
        self.ready()
        clean = copy.deepcopy(self.case.store.value("run"))
        drifted = copy.deepcopy(clean)
        changed = self.case.store.get(clean["source_after"])
        changed["revision"] = "d" * 40
        drifted.update(
            intent="drifted-attempt",
            source_after=self.case.store.save(changed),
            passed=claimed_pass,
        )
        self.case.store.append("run_intent", {"id": "drifted-attempt"})
        self.case.store.append("run", drifted)
        clean["intent"] = "clean-retry"
        self.case.store.append("run_intent", {"id": "clean-retry"})
        self.case.store.append("run", clean)
        review = copy.deepcopy(self.case.store.value("review"))
        review["run"] = self.case.store.latest("run")["object"]
        self.case.store.append("review", review)

    def test_failed_source_drift_remains_history_after_clean_retry(self):
        self.append_failed_drift_then_clean_pass()
        result = self.prepare()
        history = result["group_and_baseline_runs"]
        failed = [
            item
            for item in history
            if item["verification"] == "failed_source_drift_retained"
        ]
        self.assertEqual(len(failed), 1)
        self.assertFalse(failed[0]["passed"])
        self.assertEqual(failed[0]["evidence_use"], "history_only_no_success_authority")
        self.assertIn(
            "failed&#95;source&#95;drift&#95;retained", review_package.markdown(result)
        )

    def test_source_drift_cannot_be_relabelled_as_success_in_history(self):
        self.append_failed_drift_then_clean_pass(claimed_pass=True)
        with self.assertRaisesRegex(
            ValueError, "source-drift run cannot claim success"
        ):
            self.prepare()

    def test_same_knowledge_document_can_refresh_after_plan_change(self):
        snapshot = source.snapshot(self.case.store, str(self.case.repo))
        value = {
            "schema_version": "knowledge-v1",
            "inventory": self.case.store.latest("inventory")["object"],
            "revision": snapshot["revision"],
            "author": "synthetic-map-author",
            "citations": [],
            "nodes": [],
            "edges": [],
        }
        first = knowledge.freeze(self.case.store, str(self.case.repo), value)
        changed = copy.deepcopy(self.case.plan)
        changed["groups"][0]["rationale"] = "New attributed review of scope"
        workflow.freeze_plan(self.case.store, changed)
        with self.assertRaisesRegex(ValueError, "stale"):
            knowledge.application_map(self.case.store)
        second = knowledge.freeze(self.case.store, str(self.case.repo), value)
        self.assertEqual(first["document"], second["document"])
        self.assertNotEqual(first["plan"], second["plan"])


class PreflightTests(SourceMapCase):
    def test_missing_docker_reports_action_and_does_not_execute_application(self):
        snapshot = source.snapshot(self.store, str(self.repo))
        with (
            patch("preflight.source.snapshot", return_value=snapshot),
            patch("preflight.shutil.which", return_value=None),
            patch("preflight.subprocess.run") as run,
        ):
            result = preflight.check(self.store, str(self.repo))
        self.assertFalse(result["passed"])
        self.assertIn("no_setup", result["authority"])
        run.assert_not_called()
        self.assertFalse(
            any(
                event["kind"] in ("setup", "plan", "run")
                for event in self.store.events()
            )
        )

    def test_docker_probe_is_bounded_and_never_runs_app_or_pulls_images(self):
        calls = []

        def inspect(args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.CompletedProcess(
                args, 0, stdout=b"synthetic-engine\n", stderr=b""
            )

        snapshot = source.snapshot(self.store, str(self.repo))
        with (
            patch("preflight.source.snapshot", return_value=snapshot),
            patch("preflight.shutil.which", return_value="/synthetic/docker"),
            patch("preflight.subprocess.run", side_effect=inspect),
        ):
            result = preflight.check(self.store, str(self.repo))
        self.assertTrue(result["passed"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            calls[0][0], ["docker", "info", "--format", "{{.ServerVersion}}"]
        )
        self.assertEqual(calls[0][1]["timeout"], 30)
        self.assertFalse(result["contract_checked"])
        self.assertIn("No cloud credentials", result["limitations"][0])

    def test_docker_timeout_returns_failed_preflight(self):
        snapshot = source.snapshot(self.store, str(self.repo))
        with (
            patch("preflight.source.snapshot", return_value=snapshot),
            patch("preflight.shutil.which", return_value="/synthetic/docker"),
            patch(
                "preflight.subprocess.run",
                side_effect=subprocess.TimeoutExpired("docker", 30),
            ),
        ):
            result = preflight.check(self.store, str(self.repo))
        self.assertFalse(result["passed"])
        self.assertTrue(
            any(not item["passed"] and item["next_action"] for item in result["checks"])
        )


class PublicDemoTests(fixtures.StateCase):
    def initialize(self):
        directory = self.root / "demo"
        receipt = demo.initialize(str(directory), fixtures.IMAGE)
        return directory, receipt

    def test_public_demo_starts_unapproved_without_private_bundle_or_service(self):
        directory, receipt = self.initialize()
        contract = read_json(directory / "inputs" / "contract.json")
        plan = read_json(directory / "inputs" / "plan.json")
        self.assertEqual(receipt["review_status"], "PENDING_ACTUAL_REVIEW")
        self.assertEqual(contract["developer_confirmation"], "")
        self.assertEqual(contract["source_binding"]["level"], "unknown")
        self.assertEqual(plan["review"]["verdict"], "pending")
        self.assertFalse(plan["source_binding_accepted"])
        self.assertEqual(Store(directory / "state").events(), [])
        self.assertTrue((directory / "app" / "tests" / "test_invoice_app.py").is_file())

    def test_demo_requires_new_directory_and_immutable_image(self):
        directory, _ = self.initialize()
        with self.assertRaisesRegex(ValueError, "new canonical"):
            demo.initialize(str(directory), fixtures.IMAGE)
        with self.assertRaisesRegex(ValueError, "immutable"):
            demo.initialize(str(self.root / "other"), "python:latest")

    def test_known_variant_staging_keeps_protected_tests_and_head_exact(self):
        directory, receipt = self.initialize()
        app = directory / "app"
        protected = (app / "tests" / "test_invoice_app.py").read_bytes()
        before = source.git(app, "rev-parse", "HEAD")
        for variant in (
            "group-a",
            "group-b",
            "bad-composition",
            "repaired-composition",
        ):
            with self.subTest(variant=variant):
                demo.stage(str(directory), variant)
                self.assertEqual(
                    (app / "tests" / "test_invoice_app.py").read_bytes(), protected
                )
                self.assertEqual(source.git(app, "rev-parse", "HEAD"), before)
        self.assertIn("No application was executed", receipt["next"])

    def test_unknown_source_or_test_edits_are_preserved_and_block_staging(self):
        directory, _ = self.initialize()
        path = directory / "app" / "tests" / "test_invoice_app.py"
        path.write_bytes(path.read_bytes() + b"\n# independent local edit\n")
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "unknown source/test edits"):
            demo.stage(str(directory), "repaired-composition")
        self.assertEqual(path.read_bytes(), before)


@unittest.skipUnless(
    os.environ.get("CONTINUUM_RUN_DOCKER_TESTS") == "1", "Opt-in real Docker test"
)
class PublicDemoDockerTests(fixtures.StateCase):
    def check(self, directory, argv):
        import executor

        app = directory / "app"
        snapshot = source.snapshot(self.store, str(app))
        result = executor.run_checks(
            self.store,
            {
                "image": fixtures.IMAGE,
                "output_directories": [],
                "environment": {"PYTHONDONTWRITEBYTECODE": "1"},
            },
            snapshot,
            "candidate",
            [
                {
                    "id": "real-http-composition",
                    "kind": "integration",
                    "issue_ids": [],
                    "argv": argv,
                    "cwd": ".",
                    "timeout_seconds": 40,
                    "expected_baseline_exit": 0,
                }
            ],
        )[0]
        output = self.store.raw(result["stdout"]) + self.store.raw(result["stderr"])
        return result, output

    def test_real_http_domain_serialization_bypass_fails_security_check(self):
        directory = self.root / "demo"
        demo.initialize(str(directory), fixtures.IMAGE)
        demo.stage(str(directory), "repaired-composition")
        service = directory / "app" / "invoice_app" / "service.py"
        raw = service.read_text()
        self.assertIn("project_invoice", raw)
        # Keep authorization and the safe helper, bypass only the response projection.
        raw = raw.replace("return public_invoice", "return domain_invoice")
        self.assertNotEqual(raw, service.read_text())
        service.write_text(raw)
        result, output = self.check(
            directory,
            [
                "python",
                "-m",
                "unittest",
                "tests.test_invoice_app.SecurityRegressionTests",
            ],
        )
        self.assertFalse(result["expectation_met"])
        self.assertEqual(result["exit_code"], 1)
        self.assertIn(b"PRIVATE_FIELD_LEAK", output)


if __name__ == "__main__":
    unittest.main()
