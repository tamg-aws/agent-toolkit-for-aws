"""All records and authorization tokens are public, synthetic test fixtures."""

INVOICES = {
    101: {
        "id": 101,
        "tenant_id": "tenant-a",
        "customer": "Acme Fixtures",
        "amount_cents": 12500,
        "currency": "USD",
        "processor_token": "fixture-only-processor-reference-a",
    },
    202: {
        "id": 202,
        "tenant_id": "tenant-b",
        "customer": "Example Fixtures",
        "amount_cents": 7500,
        "currency": "EUR",
        "processor_token": "fixture-only-processor-reference-b",
    },
}

ACTOR_TOKENS = {
    "fixture-actor-a": "tenant-a",
    "fixture-actor-b": "tenant-b",
}


def load_invoice(invoice_id: int) -> dict | None:
    invoice = INVOICES.get(invoice_id)
    return dict(invoice) if invoice is not None else None
