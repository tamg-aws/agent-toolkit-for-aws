"""Transport behavior with synthetic credentials and mocked HTTPS only."""

import copy
import http.client
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))

import intake
import test_continuum_runtime as runtime_tests
from test_continuum_runtime import BASE, ENVIRONMENT, StateCase

try:
    from botocore.credentials import Credentials
except ImportError:
    Credentials = None


@unittest.skipUnless(Credentials, "botocore required for synthetic signed transport")
class SignedTransportTests(StateCase):
    def setUp(self):
        super().setUp()
        # Bypass profile/session initialization entirely. Signing uses fake
        # credentials and every HTTPS connection is replaced by a local mock.
        self.reader = intake.SignedReader.__new__(intake.SignedReader)
        self.reader.environment = ENVIRONMENT
        self.reader.region = "us-east-1"
        self.reader.host = "continuum.us-east-1.api.aws"
        self.reader.connection = None
        self.reader.session = Mock()
        self.reader.session.get_credentials.return_value = Credentials(
            "SYNTHETIC_NOT_AN_AWS_KEY", "synthetic-secret-not-valid"
        )

    @staticmethod
    def connection(status=200, body=b'{"fixture":true}'):
        response = Mock()
        response.status = status
        response.read.return_value = body
        response.getheader.return_value = "synthetic-request-id"
        connection = Mock()
        connection.getresponse.return_value = response
        return connection

    def test_retryable_http_responses_preserve_every_attempt(self):
        for status in (429, 500, 502, 503, 504):
            with self.subTest(status=status):
                first = self.connection(status, b'{"error":"synthetic"}')
                second = self.connection()
                self.reader.connection = None
                with (
                    patch.object(
                        http.client, "HTTPSConnection", side_effect=[first, second]
                    ) as connect,
                    patch.object(intake.time, "sleep") as sleep,
                ):
                    result = self.reader(BASE)
                self.assertEqual(connect.call_count, 2)
                self.assertEqual(
                    [a["http_status"] for a in result["transport_attempts"]],
                    [status, 200],
                )
                self.assertEqual(result["body"], {"fixture": True})
                first.close.assert_called_once()
                sleep.assert_called_once_with(1)

    def test_auth_or_request_error_does_not_retry(self):
        for status in (400, 401, 403, 404):
            with self.subTest(status=status):
                connection = self.connection(status, b"synthetic error")
                self.reader.connection = None
                with (
                    patch.object(
                        http.client, "HTTPSConnection", return_value=connection
                    ) as connect,
                    patch.object(intake.time, "sleep") as sleep,
                ):
                    result = self.reader(BASE)
                self.assertEqual(connect.call_count, 1)
                self.assertEqual(result["http_status"], status)
                self.assertIsNone(result["body"])
                self.assertEqual(len(result["transport_attempts"]), 1)
                sleep.assert_not_called()

    def test_three_http_failures_stop_with_all_attempts(self):
        connections = [self.connection(503) for _ in range(3)]
        with (
            patch.object(
                http.client, "HTTPSConnection", side_effect=connections
            ) as connect,
            patch.object(intake.time, "sleep") as sleep,
        ):
            result = self.reader(BASE)
        self.assertEqual(connect.call_count, 3)
        self.assertEqual(result["http_status"], 503)
        self.assertEqual(len(result["transport_attempts"]), 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1, 2])

    def test_connection_and_timeout_failures_are_bounded_and_retained(self):
        for error in (TimeoutError, ConnectionError, http.client.RemoteDisconnected):
            with self.subTest(error=error.__name__):
                connections = [self.connection() for _ in range(3)]
                for connection in connections:
                    connection.request.side_effect = error("synthetic unavailable")
                self.reader.connection = None
                with (
                    patch.object(
                        http.client, "HTTPSConnection", side_effect=connections
                    ) as connect,
                    patch.object(intake.time, "sleep"),
                ):
                    result = self.reader(BASE)
                self.assertEqual(connect.call_count, 3)
                self.assertEqual(result["http_status"], 0)
                self.assertEqual(len(result["transport_attempts"]), 3)
                self.assertEqual(
                    [a["transport_error"] for a in result["transport_attempts"]],
                    [error.__name__] * 3,
                )

    def test_successful_connection_is_reused_for_next_read(self):
        connection = self.connection()
        with patch.object(
            http.client, "HTTPSConnection", return_value=connection
        ) as connect:
            self.reader(BASE)
            self.reader(BASE + "/code-scans/fixturescan")
        connect.assert_called_once()
        self.assertEqual(connection.request.call_count, 2)
        self.assertEqual(
            [c.args[:2] for c in connection.request.call_args_list],
            [
                ("GET", BASE),
                ("GET", BASE + "/code-scans/fixturescan"),
            ],
        )

    def test_foreign_path_is_rejected_before_any_connection(self):
        for path in (
            "/environments/otherenv",
            BASE + "/code-findings/finding1/delete",
            "/latest/meta-data",
        ):
            with (
                self.subTest(path=path),
                patch.object(http.client, "HTTPSConnection") as connect,
                self.assertRaisesRegex(ValueError, "read-only"),
            ):
                self.reader(path)
            connect.assert_not_called()

    def test_invalid_success_json_is_rejected_without_retry(self):
        for body in (b'{"a":1,"a":2}', b'{"a":NaN}', b"not-json"):
            with self.subTest(body=body):
                self.reader.connection = None
                connection = self.connection(body=body)
                with (
                    patch.object(
                        http.client, "HTTPSConnection", return_value=connection
                    ) as connect,
                    patch.object(intake.time, "sleep") as sleep,
                    self.assertRaises(ValueError),
                ):
                    self.reader(BASE)
                connect.assert_called_once()
                sleep.assert_not_called()

    def test_capture_closes_reader_even_on_identity_failure(self):
        connection = self.connection()
        self.reader.connection = connection
        with (
            patch.object(
                intake,
                "_capture",
                side_effect=ValueError("Synthetic identity mismatch"),
            ) as capture,
            self.assertRaisesRegex(ValueError, "identity"),
        ):
            self.capture(self.reader)
        capture.assert_called_once()
        connection.close.assert_called_once()
        self.assertIsNone(self.reader.connection)
        self.assertEqual(self.store.events()[-1]["kind"], "capture_failed")


class SyntheticGitHub:
    def __init__(self, change=None):
        self.calls = []
        self.change = change

    def __call__(self, path):
        self.calls.append(path)
        route = path.split("?")[0]
        if route == "/repos/synthetic/fixture/pulls/7":
            body = {
                "number": 7,
                "head": {"sha": "a" * 40},
                "base": {"sha": "b" * 40, "repo": {"full_name": "synthetic/fixture"}},
                "state": "open",
                "merged": False,
                "body": "Synthetic test PR",
            }
        elif route.endswith("/check-runs"):
            body = {
                "check_runs": [
                    {
                        "id": 1,
                        "head_sha": "a" * 40,
                        "status": "completed",
                        "conclusion": "success",
                    }
                ]
            }
        elif route.endswith("/status"):
            body = {
                "sha": "a" * 40,
                "total_count": 0,
                "statuses": [],
                "state": "pending",
            }
        elif route.endswith(("/reviews", "/pulls")):
            body = []
        else:
            raise AssertionError("Unexpected synthetic provider request: " + path)
        result = {
            "path": path,
            "http_status": 200,
            "body": copy.deepcopy(body),
            "link": "",
        }
        if self.change:
            self.change(path, self.calls.count(path), result)
        result.setdefault("raw", json.dumps(result["body"]))
        return result


class ProviderReconciliationTests(StateCase):
    def reviewed_change(self):
        import provider

        case = runtime_tests.SourceAndWorkflowTests(
            methodName="test_allowed_source_edit_changes_snapshot_and_combined_diff"
        )
        case.setUp()
        self.addCleanup(case.tearDown)
        request = case.make_synthetic_reviewed_candidate()
        ready = provider.prepare(
            case.store, str(case.repo), request, lambda _: case.ownership_read()
        )
        repository = ready["repository"]["name"]
        fixture_reader = SyntheticGitHub()

        def reader(path):
            response = fixture_reader(
                path.replace("/repos/" + repository, "/repos/synthetic/fixture", 1)
            )
            response["path"] = path
            body = response["body"]
            if path.endswith("/pulls/7"):
                body["base"]["repo"]["full_name"] = repository
                body["base"]["sha"] = ready["base_sha"]
                body["head"]["sha"] = ready["head_sha"]
                body["body"] = "<!-- continuum-change:" + ready["change_id"] + " -->"
            elif "/check-runs" in path:
                body["check_runs"][0]["head_sha"] = ready["head_sha"]
            elif "/status" in path:
                body["sha"] = ready["head_sha"]
            response["raw"] = json.dumps(body)
            return response

        return case, repository, reader

    def reconcile(self, change=None):
        import provider

        return provider.reconcile(
            self.store, SyntheticGitHub(change), "synthetic/fixture", 7
        )

    def test_unbound_provider_green_cannot_assert_local_candidate_or_permission(self):
        result = self.reconcile()
        self.assertEqual(result["observed_ci"], "SUCCESS")
        self.assertEqual(result["binding"], "UNBOUND_OBSERVATION")
        self.assertEqual(result["required_checks_policy"], "UNKNOWN")
        self.assertEqual(
            result["publication_permission"], "NOT_GRANTED_BY_RECONCILIATION"
        )

    def test_wrong_repository_is_rejected(self):
        def change(path, count, response):
            if path.endswith("/pulls/7"):
                response["body"]["base"]["repo"]["full_name"] = "other/repository"

        with self.assertRaisesRegex(ValueError, "repository/number"):
            self.reconcile(change)

    def test_wrong_check_commit_is_rejected(self):
        def change(path, count, response):
            if "/check-runs" in path:
                response["body"]["check_runs"][0]["head_sha"] = "c" * 40

        with self.assertRaisesRegex(ValueError, "head differs"):
            self.reconcile(change)

    def test_head_change_during_readback_is_rejected(self):
        def change(path, count, response):
            if path.endswith("/pulls/7") and count == 2:
                response["body"]["head"]["sha"] = "c" * 40

        with self.assertRaisesRegex(ValueError, "changed"):
            self.reconcile(change)

    def test_provider_response_different_from_raw_cannot_be_used(self):
        def change(path, count, response):
            response["raw"] = '{"different":"response"}'

        with self.assertRaisesRegex(ValueError, "binding differs"):
            self.reconcile(change)

    def test_absent_or_incomplete_checks_are_not_proven_green(self):
        for mode in ("empty", "pending", "missing_status"):
            with self.subTest(mode=mode):

                def change(path, count, response, mode=mode):
                    if "/check-runs" in path:
                        if mode == "empty":
                            response["body"]["check_runs"] = []
                        elif mode == "pending":
                            response["body"]["check_runs"][0]["status"] = "in_progress"
                    if "/status" in path and mode == "missing_status":
                        response["body"]["total_count"] = 1

                result = self.reconcile(change)
                self.assertEqual(result["observed_ci"], "NOT_PROVEN")

    def test_repeated_provider_page_record_is_rejected(self):
        def change(path, count, response):
            if "/check-runs" in path:
                response["link"] = '<https://api.github.com/next>; rel="next"'

        with self.assertRaisesRegex(ValueError, "Repeated"):
            self.reconcile(change)

    def test_interrupted_new_attempt_invalidates_bound_provider_observation(self):
        import provider

        case, repository, reader = self.reviewed_change()
        before = provider.reconcile(case.store, reader, repository, 7)
        self.assertEqual(before["binding"], "MATCHED_REVIEWED_CHANGE")
        case.store.append("run_intent", {"id": "later-interrupted-attempt"})
        case.store.append(
            "run_error",
            {
                "intent": {"id": "later-interrupted-attempt"},
                "error": "Synthetic interrupted execution",
            },
        )
        after = provider.reconcile(case.store, reader, repository, 7)
        self.assertEqual(after["binding"], "UNBOUND_OBSERVATION")
        self.assertEqual(after["observed_ci"], "SUCCESS")
        self.assertEqual(
            after["publication_permission"], "NOT_GRANTED_BY_RECONCILIATION"
        )

    def test_failed_new_run_invalidates_bound_provider_observation(self):
        import provider

        case, repository, reader = self.reviewed_change()
        before = provider.reconcile(case.store, reader, repository, 7)
        self.assertEqual(before["binding"], "MATCHED_REVIEWED_CHANGE")
        failed = copy.deepcopy(case.store.value("run"))
        failed.update(intent="later-failed-attempt", passed=False)
        case.store.append("run_intent", {"id": "later-failed-attempt"})
        case.store.append("run", failed)
        after = provider.reconcile(case.store, reader, repository, 7)
        self.assertEqual(after["binding"], "UNBOUND_OBSERVATION")
        self.assertEqual(after["observed_ci"], "SUCCESS")
        self.assertEqual(
            after["publication_permission"], "NOT_GRANTED_BY_RECONCILIATION"
        )
