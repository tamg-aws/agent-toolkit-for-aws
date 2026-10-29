"""Independent acceptance tests. Service fixtures are synthetic, never live proof."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))

import contracts
import executor
import intake
import source
import workflow
from store import Store, encoded, strict_json

ACCOUNT = "111122223333"
ENVIRONMENT = "fixtureenv"
SCAN = "fixturescan"
BASE = f"/environments/{ENVIRONMENT}"
ARN = f"arn:aws:continuum:us-east-1:{ACCOUNT}:environments/{ENVIRONMENT}"
IMAGE = os.environ.get("CONTINUUM_TEST_IMAGE", "sha256:" + "a" * 64)


def export():
    return {
        "account": ACCOUNT,
        "region": "us-east-1",
        "environment_id": ENVIRONMENT,
        "scan_id": SCAN,
        "origin": "synthetic unit-test fixture, not live service evidence",
        "limitations": ["Synthetic records have no service provenance."],
        "findings": [
            {
                "findingId": key,
                "scanRunId": SCAN,
                "environmentId": ENVIRONMENT,
                "createdIssueId": "issue1",
            }
            for key in ("finding1", "finding2")
        ],
        "issues": [
            {
                "issueId": "issue1",
                "issueArn": ARN + "/code-issues/issue1",
                "findingIds": ["finding1", "finding2"],
            }
        ],
    }


class SyntheticService:
    """Exact request/response envelope with two finding pages and flat issue data."""

    def __init__(self, change=None):
        self.calls = []
        self.counts = {}
        self.change = change

    def __call__(self, path):
        self.calls.append(path)
        self.counts[path] = self.counts.get(path, 0) + 1
        parsed = urlsplit(path)
        route = parsed.path
        if route == BASE:
            body = {"environmentId": ENVIRONMENT, "environmentArn": ARN}
        elif route == BASE + "/code-scans/" + SCAN:
            body = {"scan": {"scanRunId": SCAN, "status": "COMPLETED"}}
        elif route == BASE + "/code-findings":
            if parse_qs(parsed.query).get("nextToken") == ["page2"]:
                body = {
                    "items": [
                        {"findingId": "finding2", "scanRunId": SCAN},
                        {"findingId": "otherfinding", "scanRunId": "otherscan"},
                    ]
                }
            else:
                body = {
                    "items": [{"findingId": "finding1", "scanRunId": SCAN}],
                    "nextToken": "page2",
                }
        elif route == BASE + "/code-issues":
            body = {"items": export()["issues"]}
        elif route.startswith(BASE + "/code-findings/"):
            key = route.rsplit("/", 1)[1]
            body = next(row for row in export()["findings"] if row["findingId"] == key)
        elif route == BASE + "/code-issues/issue1":
            body = export()["issues"][0]
        else:
            raise AssertionError("Unexpected service request: " + path)
        response = {
            "path": path,
            "http_status": 200,
            "body": copy.deepcopy(body),
            "request_id": "synthetic",
        }
        if self.change:
            self.change(path, self.counts[path], response)
        response.setdefault("raw", json.dumps(response["body"]))
        return response


class StateCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="continuum-runtime-test-")
        self.root = Path(self.directory.name).resolve()
        self.store = Store(self.root / "state")

    def tearDown(self):
        self.directory.cleanup()

    def capture(self, reader=None):
        return intake.capture(
            self.store,
            reader or SyntheticService(),
            ACCOUNT,
            "us-east-1",
            ENVIRONMENT,
            SCAN,
        )


class InventoryTests(StateCase):
    def test_two_pages_select_scan_without_losing_environment_count(self):
        service = SyntheticService()
        result = self.capture(service)
        self.assertEqual(result["environment_finding_count"], 3)
        self.assertEqual(result["selected_finding_count"], 2)
        self.assertEqual(result["selected_issue_count"], 1)
        self.assertEqual(set(result["findings"]), {"finding1", "finding2"})
        self.assertEqual(
            result["issues"]["issue1"]["findingIds"], ["finding1", "finding2"]
        )
        self.assertEqual(service.counts[BASE + "/code-findings/finding1"], 2)
        self.assertEqual(service.counts[BASE + "/code-findings?maxResults=100"], 2)
        self.assertTrue(all(self.store.get(key) for key in result["receipts"]))

    def reject_capture(self, change, message):
        with self.assertRaisesRegex(ValueError, message):
            self.capture(SyntheticService(change))
        self.assertFalse(
            any(event["kind"] == "inventory" for event in self.store.events())
        )
        self.assertTrue(list((self.store.root / "objects").iterdir()))

    def test_missing_scan_id_cannot_silently_exclude_a_finding(self):
        def change(path, count, response):
            if path == BASE + "/code-findings?maxResults=100":
                del response["body"]["items"][0]["scanRunId"]

        self.reject_capture(change, "identifier")

    def test_conflicting_summary_environment_is_rejected(self):
        def change(path, count, response):
            if path == BASE + "/code-findings?maxResults=100":
                response["body"]["items"][0]["environmentId"] = "wrongenv"

        self.reject_capture(change, "environment")

    def test_wrong_environment_account_is_rejected(self):
        def change(path, count, response):
            if path == BASE:
                response["body"]["environmentArn"] = ARN.replace(
                    ACCOUNT, "999988887777"
                )

        self.reject_capture(change, "identity")

    def test_detail_identity_must_match_selected_finding(self):
        def change(path, count, response):
            if path == BASE + "/code-findings/finding1":
                response["body"]["scanRunId"] = "otherscan"

        self.reject_capture(change, "identity")

    def test_repeated_cursor_does_not_mark_import_complete(self):
        def change(path, count, response):
            if "nextToken=page2" in path:
                response["body"] = {"items": [], "nextToken": "page2"}

        self.reject_capture(change, "pagination")

    def test_duplicate_page_record_is_not_silently_deduplicated(self):
        def change(path, count, response):
            if "nextToken=page2" in path:
                response["body"]["items"][0]["findingId"] = "finding1"

        self.reject_capture(change, "Duplicate inventory")

    def test_failed_detail_read_does_not_commit_inventory(self):
        def change(path, count, response):
            if path == BASE + "/code-findings/finding1":
                response["http_status"] = 503

        self.reject_capture(change, "transport")

    def test_decoded_body_cannot_differ_from_retained_bytes(self):
        def change(path, count, response):
            response["raw"] = "{}"

        self.reject_capture(change, "retained bytes")

    def test_detail_drift_without_list_drift_is_detected(self):
        def change(path, count, response):
            if path == BASE + "/code-findings/finding1" and count == 2:
                response["body"]["description"] = "changed without listing update"

        self.reject_capture(change, "Finding changed")

    def test_listing_drift_is_detected(self):
        def change(path, count, response):
            if path == BASE + "/code-findings?maxResults=100" and count == 2:
                response["body"]["items"][0]["state"] = "changed"

        self.reject_capture(change, "Inventory changed")

    def test_issue_arn_cannot_claim_another_environment(self):
        def change(path, count, response):
            if path == BASE + "/code-issues/issue1":
                response["body"]["issueArn"] = (
                    ARN.replace(ENVIRONMENT, "otherenv") + "/code-issues/issue1"
                )

        self.reject_capture(change, "Issue identity")

    def test_export_is_explicitly_unverified_and_original_is_retained(self):
        result = intake.import_export(self.store, export())
        self.assertEqual(result["evidence_class"], "imported_service_export")
        self.assertEqual(result["completeness"], "not_independently_verified")
        self.assertEqual(self.store.get(result["original_export"]), export())

    def test_export_duplicate_finding_is_rejected(self):
        value = export()
        value["findings"].append(copy.deepcopy(value["findings"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            intake.import_export(self.store, value)


class EvidenceStoreTests(StateCase):
    def test_json_duplicate_keys_and_nonfinite_numbers_are_rejected(self):
        for value in (
            b'{"a":1,"a":2}',
            b'{"a":NaN}',
            b'{"a":Infinity}',
            b'{"a":-Infinity}',
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                strict_json(value)

    def test_changed_object_bytes_are_rejected(self):
        key = self.store.save({"verdict": "failed"})
        (self.store.root / "objects" / key).write_bytes(encoded({"verdict": "passed"}))
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.store.get(key)

    def test_missing_middle_event_is_rejected(self):
        for number in range(3):
            self.store.append("capture_failed", {"number": number})
        (self.store.root / "events" / "000001.json").unlink()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.store.events()

    def test_unknown_event_version_is_rejected(self):
        self.store.append("capture_failed", {"value": 1})
        path = self.store.root / "events" / "000000.json"
        value = json.loads(path.read_text())
        value["schema_version"] = "unsupported-future-version"
        path.write_bytes(encoded(value))
        with self.assertRaises(ValueError):
            self.store.events()

    def test_symlink_object_is_rejected_even_if_bytes_match(self):
        key = self.store.save({"verdict": "failed"})
        path = self.store.root / "objects" / key
        saved = self.root / "copied-object"
        saved.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(saved)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.store.get(key)


def app_contract(revision):
    checks = []
    for key in ("issue-a", "issue-b"):
        checks.extend(
            [
                {
                    "id": key + "-negative",
                    "kind": "negative",
                    "issue_ids": [key],
                    "argv": [
                        "python",
                        "-c",
                        "raise AssertionError('EXPECTED_SECURITY_RED')",
                    ],
                    "cwd": ".",
                    "timeout_seconds": 10,
                    "expected_baseline_exit": 1,
                    "baseline_signature": "EXPECTED_SECURITY_RED",
                },
                {
                    "id": key + "-valid",
                    "kind": "valid",
                    "issue_ids": [key],
                    "argv": ["python", "-c", "assert 1 + 1 == 2"],
                    "cwd": ".",
                    "timeout_seconds": 10,
                    "expected_baseline_exit": 0,
                },
            ]
        )
    for kind in ("build", "lint", "unit", "integration", "smoke"):
        checks.append(
            {
                "id": kind,
                "kind": kind,
                "issue_ids": [],
                "argv": ["python", "-c", "assert True"],
                "cwd": ".",
                "timeout_seconds": 10,
                "expected_baseline_exit": 0,
            }
        )
    return {
        "schema_version": "application-contract-v1",
        "author": "fixture-author",
        "developer_confirmation": "Synthetic contract validator case; not application test evidence.",
        "repository": {"provider": "github", "name": "synthetic-fixture/invoice"},
        "source_binding": {
            "revision": revision,
            "environment_id": ENVIRONMENT,
            "scan_id": SCAN,
            "level": "independently_compared",
            "evidence": "Synthetic source binding only.",
        },
        "allowed_paths": ["app.py", "other.py"],
        "protected_paths": ["test_app.py"],
        "checks": checks,
        "image": IMAGE,
        "max_candidate_runs": 4,
        "output_directories": [],
    }


def change_plan(baseline_key):
    return {
        "schema_version": "change-plan-v1",
        "baseline_snapshot": baseline_key,
        "author": "fixture-author",
        "review": {
            "reviewer": "fixture-reviewer",
            "verdict": "approved",
            "evidence": "Synthetic independent review record.",
        },
        "source_binding_accepted": True,
        "findings": [
            {
                "finding_id": finding,
                "disposition": "selected",
                "issue_id": issue,
                "reason": "Synthetic distinct issue.",
                "evidence": "Synthetic fixture source.",
            }
            for finding, issue in (("finding1", "issue-a"), ("finding2", "issue-b"))
        ],
        "issues": [
            {
                "id": issue,
                "group_id": group,
                "finding_ids": [finding],
                "root_cause": "Synthetic root cause.",
                "source_evidence": "app.py at baseline fixture.",
                "behavior": "Preserve legitimate behavior.",
                "paths": [path],
            }
            for finding, issue, group, path in (
                ("finding1", "issue-a", "group-a", "app.py"),
                ("finding2", "issue-b", "group-b", "other.py"),
            )
        ],
        "groups": [
            {"id": key, "rationale": "Synthetic separate mechanism.", "depends_on": []}
            for key in ("group-a", "group-b")
        ],
        "interactions": [
            {
                "from": "group-a",
                "to": "group-b",
                "verdict": "coupled",
                "reason": "Both changes affect the response pipeline.",
                "evidence": "Synthetic call-order relationship.",
                "reviewer": "fixture-reviewer",
            }
        ],
    }


class ContractAndPlanTests(StateCase):
    def setUp(self):
        super().setUp()
        self.inventory = intake.import_export(self.store, export())
        self.app = app_contract("a" * 40)
        self.baseline = {
            "revision": "a" * 40,
            "files": {"app.py": {}, "other.py": {}, "test_app.py": {}},
        }
        self.plan = change_plan("b" * 64)

    def validate(self):
        return contracts.plan(self.plan, self.inventory, self.app, "b" * 64)

    def test_supported_contract_and_full_plan_are_accepted(self):
        self.assertIs(
            contracts.contract(self.app, self.baseline, self.inventory), self.app
        )
        self.assertIs(self.validate(), self.plan)

    def test_each_finding_must_be_accounted_once(self):
        for mode in ("missing", "duplicate"):
            with self.subTest(mode=mode):
                self.plan = change_plan("b" * 64)
                if mode == "missing":
                    self.plan["findings"].pop()
                else:
                    self.plan["findings"].append(
                        copy.deepcopy(self.plan["findings"][0])
                    )
                with self.assertRaisesRegex(ValueError, "every"):
                    self.validate()

    def test_duplicate_cycles_and_chains_have_no_canonical_target(self):
        self.inventory["findings"].update({"finding3": {}, "finding4": {}})
        for targets in (("finding4", "finding3"), ("finding4", "finding1")):
            with self.subTest(targets=targets):
                self.plan = change_plan("b" * 64)
                self.plan["findings"] += [
                    {
                        "finding_id": key,
                        "disposition": "duplicate",
                        "duplicate_of": target,
                        "reason": "Synthetic duplicate test.",
                        "evidence": "Synthetic relationship.",
                    }
                    for key, target in zip(("finding3", "finding4"), targets)
                ]
                with self.assertRaises(ValueError):
                    self.validate()

    def test_distinct_related_issues_stay_separate_despite_coupled_group_edge(self):
        self.validate()
        self.assertEqual(len(self.plan["issues"]), 2)
        self.assertEqual(
            {row["disposition"] for row in self.plan["findings"]}, {"selected"}
        )

    def test_group_cycles_are_rejected(self):
        self.plan["groups"][0]["depends_on"] = ["group-b"]
        self.plan["groups"][1]["depends_on"] = ["group-a"]
        with self.assertRaisesRegex(ValueError, "cycle"):
            self.validate()

    def test_missing_pairwise_interaction_is_rejected(self):
        self.plan["interactions"] = []
        with self.assertRaisesRegex(ValueError, "interaction"):
            self.validate()

    def test_negative_regression_cannot_replace_legitimate_control(self):
        self.app["checks"] = [
            check for check in self.app["checks"] if check["id"] != "issue-a-valid"
        ]
        with self.assertRaisesRegex(ValueError, "valid"):
            self.validate()

    def test_baseline_error_exit_and_signature_must_be_explicit(self):
        for change in ({"expected_baseline_exit": 0}, {"baseline_signature": ""}):
            with self.subTest(change=change):
                app = app_contract("a" * 40)
                app["checks"][0].update(change)
                with self.assertRaises(ValueError):
                    contracts.contract(app, self.baseline, self.inventory)

    def test_one_negative_failure_cannot_prove_two_distinct_issues(self):
        self.app["checks"][0]["issue_ids"] = ["issue-a", "issue-b"]
        with self.assertRaisesRegex(ValueError, "exactly one issue"):
            contracts.contract(self.app, self.baseline, self.inventory)

    def test_protected_files_cannot_be_allowed_candidate_paths(self):
        self.app["allowed_paths"].append("test_app.py")
        with self.assertRaisesRegex(ValueError, "Protected"):
            contracts.contract(self.app, self.baseline, self.inventory)

    def test_output_mount_cannot_hide_source_or_protected_tests(self):
        self.app["output_directories"] = ["test_app.py"]
        with self.assertRaisesRegex(ValueError, "hide"):
            contracts.contract(self.app, self.baseline, self.inventory)

    def test_output_mount_delimiters_and_control_characters_are_rejected(self):
        for path in ("out,readonly=false", "out,bind-propagation=shared", "out\tname"):
            with self.subTest(path=path):
                self.app["output_directories"] = [path]
                with self.assertRaisesRegex(ValueError, "delimiters/control"):
                    contracts.contract(self.app, self.baseline, self.inventory)

    def test_interaction_map_endpoints_resolve_to_existing_nodes(self):
        with patch.object(
            workflow,
            "active",
            return_value=({}, self.inventory, self.baseline, self.app, self.plan),
        ):
            self.store.append("plan", {"plan": self.store.save(self.plan)})
            result = workflow.application_map(self.store)
        node_ids = {node["id"] for node in result["nodes"]}
        for edge in result["edges"]:
            self.assertIn(edge["from"], node_ids)
            self.assertIn(edge["to"], node_ids)


class SourceAndWorkflowTests(StateCase):
    def setUp(self):
        super().setUp()
        self.repo = self.root / "app"
        self.repo.mkdir()
        for name in ("app.py", "other.py", "test_app.py"):
            (self.repo / name).write_text("value = 1\n")
        for args in (
            ["init", "-b", "fixture"],
            ["add", "."],
            [
                "-c",
                "user.name=Runtime Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-m",
                "Create synthetic source fixture",
            ],
        ):
            subprocess.run(
                ["git", "-c", "core.hooksPath=/dev/null", *args],
                cwd=self.repo,
                check=True,
                capture_output=True,
            )
        intake.import_export(self.store, export())
        self.revision = source.git(self.repo, "rev-parse", "HEAD").decode().strip()
        self.app = app_contract(self.revision)
        self.settings = workflow.setup(self.store, str(self.repo), self.app)
        self.plan = change_plan(self.settings["baseline"])
        workflow.freeze_plan(self.store, self.plan)

    def test_allowed_source_edit_changes_snapshot_and_combined_diff(self):
        (self.repo / "app.py").write_text("value = 2\n")
        candidate, changed = workflow.current(self.store, str(self.repo))
        self.assertEqual(changed, ["app.py"])
        diff = workflow.combined_diff(
            self.store, self.store.get(self.settings["baseline"]), candidate
        )
        self.assertIn("-value = 1", diff)
        self.assertIn("+value = 2", diff)

    def test_changed_protected_test_is_rejected(self):
        (self.repo / "test_app.py").write_text("assert True\n")
        with self.assertRaisesRegex(ValueError, "protected"):
            workflow.current(self.store, str(self.repo))

    def test_unapproved_new_file_is_rejected(self):
        (self.repo / "surprise.py").write_text("print('surprise')\n")
        with self.assertRaisesRegex(ValueError, "unapproved"):
            workflow.current(self.store, str(self.repo))

    def test_allowed_deletion_is_included_in_combined_diff(self):
        (self.repo / "app.py").unlink()
        candidate, changed = workflow.current(self.store, str(self.repo))
        self.assertEqual(changed, ["app.py"])
        self.assertNotIn("app.py", candidate["files"])
        diff = workflow.combined_diff(
            self.store, self.store.get(self.settings["baseline"]), candidate
        )
        self.assertIn("-value = 1", diff)

    def test_deleted_protected_test_is_rejected(self):
        (self.repo / "test_app.py").unlink()
        with self.assertRaisesRegex(ValueError, "protected"):
            workflow.current(self.store, str(self.repo))

    def test_symlink_source_cannot_read_outside_repository(self):
        (self.root / "outside").write_text("synthetic host-only canary")
        (self.repo / "app.py").unlink()
        (self.repo / "app.py").symlink_to(self.root / "outside")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            workflow.current(self.store, str(self.repo))

    def test_mode_changes_are_rejected(self):
        (self.repo / "app.py").chmod(0o755)
        with self.assertRaisesRegex(ValueError, "mode"):
            workflow.current(self.store, str(self.repo))

    def test_authoritative_state_cannot_live_inside_app(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            source.snapshot(Store(self.repo / "state"), str(self.repo))

    def test_path_traversal_and_git_internals_are_rejected(self):
        for path in (
            "../app.py",
            "/tmp/app.py",
            "x/../../app.py",
            ".git/config",
            "x\\app.py",
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                source.relative(path)

    def test_changed_plan_requires_new_baseline_evidence(self):
        self.plan["groups"][0]["rationale"] = "Updated scope explanation."
        workflow.freeze_plan(self.store, self.plan)
        with self.assertRaisesRegex(ValueError, "baseline proof"):
            workflow.run(self.store, str(self.repo), "candidate")

    def test_unresolved_execution_intent_cannot_be_retried_silently(self):
        self.store.append("run_intent", {"id": "unfinished"})
        with self.assertRaisesRegex(ValueError, "Unresolved"):
            workflow.run(self.store, str(self.repo), "baseline")

    def make_synthetic_reviewed_candidate(self):
        """Construct gate inputs, never real execution proof or a live PR."""
        (self.repo / "app.py").write_text("value = 2\n")
        candidate, _changed = workflow.current(self.store, str(self.repo))
        snapshot = self.store.save(candidate)
        checks = [
            {
                "check": check,
                "evidence_class": "supervised_container_execution",
                "stdout": self.store.put(b""),
                "stderr": self.store.put(b""),
                "image_receipt": self.store.save({"Id": IMAGE}),
                "cause": "exited",
                "exit_code": 0,
                "expected_exit": 0,
                "expectation_met": True,
            }
            for check in self.app["checks"]
        ]
        record = {
            "evidence_class": "supervised_container_execution",
            "intent": "synthetic-candidate-intent",
            "setup": self.store.latest("setup")["object"],
            "plan": self.store.latest("plan")["object"],
            "phase": "candidate",
            "source_before": snapshot,
            "source_after": snapshot,
            "passed": True,
            "checks": checks,
        }
        self.store.append("run_intent", {"id": "synthetic-candidate-intent"})
        run_event = self.store.append("run", record)
        diff = self.store.put(
            workflow.combined_diff(
                self.store, self.store.get(self.settings["baseline"]), candidate
            ).encode()
        )
        review = {
            "run": run_event["object"],
            "source": snapshot,
            "verdict": "approved",
            "reviewer": "synthetic-independent-reviewer",
            "rationale": "Synthetic gate test, not a real execution review.",
            "residual_risk": "Synthetic gate inputs only.",
            "diff_sha256": diff,
            "interaction_review": True,
        }
        workflow.review(self.store, str(self.repo), review)
        source.git(self.repo, "add", "app.py")
        source.git(
            self.repo,
            "-c",
            "user.name=Runtime Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-m",
            "Create synthetic candidate commit",
        )
        return {
            "title": "Synthetic publication guard test",
            "body": "Synthetic gate fixtures only; no application fix is asserted.",
            "disclosure_review": "All data is synthetic.",
        }

    @staticmethod
    def ownership_read(policy="DISABLED"):
        body = {
            "environmentId": ENVIRONMENT,
            "environmentArn": ARN,
            "configuration": {
                "codeConfiguration": {
                    "environmentConfiguration": {"patchCreationPolicy": policy}
                }
            },
        }
        return {
            "path": BASE,
            "http_status": 200,
            "raw": json.dumps(body),
            "body": body,
        }

    def test_unknown_or_enabled_patch_ownership_blocks_publication(self):
        import provider

        request = self.make_synthetic_reviewed_candidate()
        for policy in (None, "ENABLED", "UNKNOWN"):
            reader = (
                None
                if policy is None
                else lambda _, policy=policy: self.ownership_read(policy)
            )
            with self.subTest(policy=policy):
                result = provider.prepare(self.store, str(self.repo), request, reader)
                self.assertEqual(result["status"], "PUBLICATION_BLOCKED")

    def test_prepared_pr_identity_is_stable_but_does_not_create_a_pr(self):
        import provider

        request = self.make_synthetic_reviewed_candidate()
        first = provider.prepare(
            self.store, str(self.repo), request, lambda _: self.ownership_read()
        )
        second = provider.prepare(
            self.store, str(self.repo), request, lambda _: self.ownership_read()
        )
        self.assertEqual(first["status"], "NEEDS_PROVIDER_OWNERSHIP_RECONCILIATION")
        self.assertEqual(first["change_id"], second["change_id"])
        self.assertEqual(first["body"], second["body"])
        self.assertIn("No provider write is implemented", first["limitations"][0])

    def test_mutation_after_review_cannot_be_prepared(self):
        import provider

        request = self.make_synthetic_reviewed_candidate()
        (self.repo / "app.py").write_text("value = 3\n")
        with self.assertRaisesRegex(ValueError, "approved passing source"):
            provider.prepare(self.store, str(self.repo), request)

    def test_stale_plan_review_cannot_be_prepared(self):
        import provider

        request = self.make_synthetic_reviewed_candidate()
        self.plan["groups"][0]["rationale"] = "New synthetic scope rationale."
        workflow.freeze_plan(self.store, self.plan)
        with self.assertRaisesRegex(ValueError, "stale"):
            provider.prepare(self.store, str(self.repo), request)

    def test_new_unresolved_intent_invalidates_previous_review(self):
        import provider

        request = self.make_synthetic_reviewed_candidate()
        self.store.append("run_intent", {"id": "new-incomplete-attempt"})
        with self.assertRaisesRegex(ValueError, "unresolved or newer"):
            provider.prepare(self.store, str(self.repo), request)

    def test_new_failed_run_invalidates_previous_review(self):
        import provider

        request = self.make_synthetic_reviewed_candidate()
        failed = copy.deepcopy(self.store.value("run"))
        failed.update(intent="new-failed-attempt", passed=False)
        self.store.append("run_intent", {"id": "new-failed-attempt"})
        self.store.append("run", failed)
        with self.assertRaisesRegex(ValueError, "stale"):
            provider.prepare(self.store, str(self.repo), request)

    def test_ownership_from_another_environment_cannot_enable_publication(self):
        import provider

        request = self.make_synthetic_reviewed_candidate()
        response = self.ownership_read()
        response["body"]["environmentId"] = "otherenv"
        response["raw"] = json.dumps(response["body"])
        with self.assertRaisesRegex(ValueError, "environment differs"):
            provider.prepare(self.store, str(self.repo), request, lambda _: response)


class ExecutionProofTests(StateCase):
    def record(self):
        check = app_contract("a" * 40)["checks"][0]
        app = {"checks": [check]}
        setup = self.store.save({"contract": self.store.save(app)})
        snapshot = self.store.save({"revision": "a" * 40, "files": {}})
        result = {
            "evidence_class": "supervised_container_execution",
            "setup": setup,
            "phase": "baseline",
            "source_before": snapshot,
            "source_after": snapshot,
            "passed": True,
            "checks": [
                {
                    "check": check,
                    "evidence_class": "supervised_container_execution",
                    "stdout": self.store.put(b""),
                    "stderr": self.store.put(
                        b"AssertionError: EXPECTED_SECURITY_RED\n"
                    ),
                    "image_receipt": self.store.save({"Id": IMAGE}),
                    "cause": "exited",
                    "exit_code": 1,
                    "expected_exit": 1,
                    "expectation_met": True,
                }
            ],
        }
        return result

    def test_unrelated_failure_does_not_count_as_expected_security_red(self):
        record = self.record()
        record["checks"][0]["stderr"] = self.store.put(
            b"ModuleNotFoundError: missing_dependency\n"
        )
        with self.assertRaises(ValueError):
            workflow.verify_run(self.store, record)

    def test_claimed_green_with_wrong_exit_cannot_pass_receipt_validation(self):
        record = self.record()
        record["checks"][0]["exit_code"] = 0
        with self.assertRaises(ValueError):
            workflow.verify_run(self.store, record)

    def test_source_mutation_invalidates_even_green_checks(self):
        record = self.record()
        record["source_after"] = self.store.save({"revision": "different"})
        with self.assertRaisesRegex(ValueError, "Source changed"):
            workflow.verify_run(self.store, record)

    def test_missing_required_check_cannot_be_promoted_by_passed_flag(self):
        record = self.record()
        record["checks"] = []
        with self.assertRaisesRegex(ValueError, "sequence"):
            workflow.verify_run(self.store, record)


class SupervisorProcessTests(StateCase):
    def supervise_synthetic_process(self, state, child_exit=0):
        # The local child is real; Docker inspection is mocked to exercise
        # inconsistent supervisor signals without needing a failed daemon.
        popen = subprocess.Popen
        process_argv = [
            sys.executable,
            "-c",
            f"print('SYNTHETIC_SUPERVISOR_OUTPUT');raise SystemExit({child_exit})",
        ]
        with (
            patch.object(
                executor.subprocess,
                "Popen",
                side_effect=lambda *args, **kwargs: popen(process_argv, **kwargs),
            ),
            patch.object(
                executor, "docker", return_value=json.dumps([{"State": state}]).encode()
            ),
        ):
            return executor.supervise(self.store, "synthetic-container", 5)

    @staticmethod
    def completed_state():
        return {
            "Running": False,
            "Status": "exited",
            "ExitCode": 0,
            "OOMKilled": False,
            "Error": "",
            "StartedAt": "2026-01-01T00:00:00Z",
            "FinishedAt": "2026-01-01T00:00:01Z",
        }

    def test_never_started_or_abnormal_container_cannot_report_green(self):
        for change in (
            {"Status": "created"},
            {"StartedAt": "0001-01-01T00:00:00Z"},
            {"FinishedAt": "0001-01-01T00:00:00Z"},
            {"OOMKilled": True},
            {"Error": "Synthetic daemon failure"},
            {"ExitCode": 1},
        ):
            with self.subTest(change=change):
                state = dict(self.completed_state(), **change)
                result = self.supervise_synthetic_process(state)
                self.assertEqual(result["cause"], "infrastructure_failure")

    def test_failed_attach_is_not_success_even_if_container_exit_is_zero(self):
        result = self.supervise_synthetic_process(self.completed_state(), child_exit=1)
        self.assertEqual(result["attach_exit_code"], 1)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["cause"], "infrastructure_failure")

    def test_matching_real_child_exit_and_container_state_retains_output(self):
        result = self.supervise_synthetic_process(self.completed_state())
        self.assertEqual(result["cause"], "exited")
        self.assertIn(b"SYNTHETIC_SUPERVISOR_OUTPUT", self.store.raw(result["stdout"]))


@unittest.skipUnless(
    os.environ.get("CONTINUUM_RUN_DOCKER_TESTS") == "1", "opt-in real Docker checks"
)
class DockerIsolationTests(StateCase):
    def test_real_child_cannot_read_host_or_write_authoritative_evidence(self):
        canary = self.root / "host-canary"
        canary.write_text("synthetic-host-only-canary")
        marker = self.store.root / "forged-receipt"
        program = (
            "import json,os,pathlib,socket\n"
            f"assert not pathlib.Path({str(canary)!r}).exists()\n"
            f"p=pathlib.Path({str(marker)!r})\n"
            "try:\n p.write_text('forged')\nexcept OSError:\n pass\n"
            "else:\n raise AssertionError('authoritative path unexpectedly writable')\n"
            "assert not pathlib.Path('/var/run/docker.sock').exists()\n"
            "assert not pathlib.Path('/run/host-services/ssh-auth.sock').exists()\n"
            "assert not any(k in os.environ for k in "
            "['AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN','AWS_PROFILE','SSH_AUTH_SOCK'])\n"
            "pathlib.Path('/tmp/legitimate-output').write_text('ok')\n"
            "s=socket.socket();s.settimeout(.2)\n"
            "try:\n s.connect(('169.254.169.254',80))\n"
            "except OSError:\n pass\n"
            "else:\n raise AssertionError('metadata endpoint reachable')\n"
            "finally:\n s.close()\n"
            "print('HOST_AND_CONTROL_BOUNDARIES_ENFORCED')\n"
        )
        snapshot = {
            "revision": "a" * 40,
            "files": {
                "probe.py": {
                    "sha256": self.store.put(program.encode()),
                    "bytes": len(program.encode()),
                    "mode": "644",
                }
            },
        }
        check = {
            "id": "host-isolation",
            "kind": "smoke",
            "issue_ids": [],
            "argv": ["python", "probe.py"],
            "cwd": ".",
            "timeout_seconds": 20,
            "expected_baseline_exit": 0,
        }
        records = executor.run_checks(
            self.store,
            {"image": IMAGE, "output_directories": [], "environment": {}},
            snapshot,
            "candidate",
            [check],
        )
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0]["expectation_met"])
        self.assertIn(
            b"HOST_AND_CONTROL_BOUNDARIES_ENFORCED",
            self.store.raw(records[0]["stdout"]),
        )
        self.assertFalse(marker.exists())
        self.assertEqual(canary.read_text(), "synthetic-host-only-canary")

    def test_real_import_error_is_not_security_baseline_proof(self):
        body = b"import deliberately_absent_fixture_dependency\n"
        snapshot = {
            "revision": "a" * 40,
            "files": {
                "probe.py": {
                    "sha256": self.store.put(body),
                    "bytes": len(body),
                    "mode": "644",
                }
            },
        }
        check = {
            "id": "unrelated-import-error",
            "kind": "negative",
            "issue_ids": ["fixture-issue"],
            "argv": ["python", "probe.py"],
            "cwd": ".",
            "timeout_seconds": 20,
            "expected_baseline_exit": 1,
            "baseline_signature": "EXPECTED_SECURITY_RED",
        }
        records = executor.run_checks(
            self.store,
            {"image": IMAGE, "output_directories": [], "environment": {}},
            snapshot,
            "baseline",
            [check],
        )
        self.assertEqual(records[0]["exit_code"], 1)
        self.assertIn(b"ModuleNotFoundError", self.store.raw(records[0]["stderr"]))
        self.assertFalse(records[0]["expectation_met"])


if __name__ == "__main__":
    unittest.main()
