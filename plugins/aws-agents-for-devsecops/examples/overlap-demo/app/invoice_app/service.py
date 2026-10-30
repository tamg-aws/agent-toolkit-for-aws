from invoice_app.authorization import authorize_invoice
from invoice_app.presentation import project_invoice
from invoice_app.store import load_invoice


def read_invoice(invoice_id: int, actor_tenant: str) -> dict:
    domain_invoice = load_invoice(invoice_id)
    if domain_invoice is None:
        raise LookupError("Invoice not found")
    public_invoice = project_invoice(domain_invoice)
    authorize_invoice(public_invoice, actor_tenant)
    return public_invoice
