import json
import threading
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from invoice_app.http_api import make_server
from invoice_app.presentation import project_invoice
from invoice_app.store import load_invoice


class HttpFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = make_server()
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}
        )
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        if cls.thread.is_alive():
            raise RuntimeError("Fixture HTTP server did not stop")

    def get(self, path: str, token: str | None = "fixture-actor-a") -> tuple:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        request = urllib.request.Request(self.base_url + path, headers=headers)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            response = opener.open(request, timeout=3)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return (
                response.status,
                json.load(response),
                response.headers.get("Content-Type"),
            )


class SecurityRegressionTests(HttpFixture):
    def test_cross_tenant_invoice_denied(self) -> None:
        for token, invoice_id in (
            ("fixture-actor-a", 202),
            ("fixture-actor-b", 101),
        ):
            with self.subTest(token=token):
                status, body, _ = self.get(f"/invoices/{invoice_id}", token)
                self.assertEqual(
                    status,
                    403,
                    "IDOR_CROSS_TENANT_READ: another tenant's invoice leaked",
                )
                self.assertEqual(body, {"error": "forbidden"})

    def test_public_projection_excludes_processor_token(self) -> None:
        for invoice_id in (101, 202):
            with self.subTest(invoice_id=invoice_id):
                domain_invoice = load_invoice(invoice_id)
                self.assertNotIn(
                    "processor_token",
                    project_invoice(domain_invoice),
                    "PRIVATE_FIELD_LEAK: processor reference appears in public response",
                )
                self.assertIn("processor_token", domain_invoice)
        for token, invoice_id in (
            ("fixture-actor-a", 101),
            ("fixture-actor-b", 202),
        ):
            with self.subTest(http_invoice_id=invoice_id):
                status, body, _ = self.get(f"/invoices/{invoice_id}", token)
                self.assertIn(status, (200, 403))
                if status == 200:
                    for field in ("processor_token", "tenant_id"):
                        self.assertNotIn(
                            field,
                            body,
                            "PRIVATE_FIELD_LEAK: private field appears in HTTP response",
                        )
                else:
                    self.assertEqual(body, {"error": "forbidden"})


class ValidBehaviorTests(HttpFixture):
    def test_tenant_a_reads_own_invoice(self) -> None:
        status, body, content_type = self.get("/invoices/101")
        self.assertEqual(
            status, 200, "VALID_TENANT_READ_BROKEN: tenant-a must read its own invoice"
        )
        self.assertEqual(content_type, "application/json")
        self.assertEqual(body["id"], 101)
        self.assertEqual(body["customer"], "Acme Fixtures")
        self.assertEqual(body["amount_cents"], 12500)
        self.assertEqual(body["currency"], "USD")

    def test_tenant_b_reads_own_invoice(self) -> None:
        status, body, _ = self.get("/invoices/202", "fixture-actor-b")
        self.assertEqual(
            status, 200, "VALID_TENANT_READ_BROKEN: tenant-b must read its own invoice"
        )
        self.assertEqual(body["id"], 202)
        self.assertEqual(body["amount_cents"], 7500)
        self.assertEqual(body["currency"], "EUR")

    def test_unknown_invoice_returns_404(self) -> None:
        self.assertEqual(self.get("/invoices/999")[0], 404)

    def test_missing_or_unknown_actor_is_unauthenticated(self) -> None:
        for token in (None, "unknown-fixture-actor"):
            with self.subTest(token=token):
                status, body, _ = self.get("/invoices/101", token)
                self.assertEqual(status, 401)
                self.assertEqual(body, {"error": "unauthenticated"})

    def test_health_is_available_without_actor(self) -> None:
        status, body, _ = self.get("/health", None)
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_unknown_route_returns_404(self) -> None:
        self.assertEqual(self.get("/other")[0], 404)


class IntegrationSmokeTests(HttpFixture):
    def test_concurrent_legitimate_reads_preserve_tenant_data(self) -> None:
        requests = [
            (101, "fixture-actor-a", 12500),
            (202, "fixture-actor-b", 7500),
        ] * 10

        def fetch(item: tuple) -> tuple:
            invoice_id, token, amount = item
            return invoice_id, amount, self.get(f"/invoices/{invoice_id}", token)

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(fetch, requests))
        for invoice_id, amount, (status, body, _) in results:
            self.assertEqual(
                status,
                200,
                "COMPOSED_APP_REGRESSION: legitimate parallel read rejected",
            )
            self.assertEqual(body["id"], invoice_id)
            self.assertEqual(body["amount_cents"], amount)

    def test_projection_does_not_modify_stored_domain_invoice(self) -> None:
        before = load_invoice(101)
        project_invoice(before)
        self.assertEqual(before, load_invoice(101))

    def test_unknown_and_health_requests_do_not_break_valid_read(self) -> None:
        self.assertEqual(self.get("/invoices/999")[0], 404)
        self.assertEqual(self.get("/health", None)[0], 200)
        self.assertEqual(
            self.get("/invoices/101")[0],
            200,
            "COMPOSED_APP_REGRESSION: valid read must survive other request types",
        )
