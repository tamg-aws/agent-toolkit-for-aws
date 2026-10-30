import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from invoice_app.service import read_invoice
from invoice_app.store import ACTOR_TOKENS


class InvoiceHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/health":
            self.reply(200, {"status": "ok"})
            return
        actor = ACTOR_TOKENS.get(
            self.headers.get("Authorization", "").removeprefix("Bearer ")
        )
        if actor is None:
            self.reply(401, {"error": "unauthenticated"})
            return
        parts = path.strip("/").split("/")
        if len(parts) != 2 or parts[0] != "invoices" or not parts[1].isdecimal():
            self.reply(404, {"error": "not found"})
            return
        try:
            invoice = read_invoice(int(parts[1]), actor)
        except LookupError:
            self.reply(404, {"error": "not found"})
            return
        except PermissionError:
            self.reply(403, {"error": "forbidden"})
            return
        self.reply(200, invoice)

    def reply(self, status: int, body: dict) -> None:
        payload = json.dumps(body, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        pass


def make_server() -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", 0), InvoiceHandler)
