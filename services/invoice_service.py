from typing import AsyncGenerator

from db_models import Invoice
from exceptions import InvoiceDeleteError, InvalidStatusChangeError
from schemas import Status, STATUS_MAP, InvoiceResponse


def draft_invoice_checker(invoice: Invoice) -> None:
    if invoice.status != Status.draft:
        raise InvoiceDeleteError("Not allowed to delete invoices that was sent already ")


def valid_status_change(old_status: Status, new_status: Status) -> None:
    if not (new_status in STATUS_MAP[old_status]):
        raise InvalidStatusChangeError(from_status=old_status, to_status=new_status)


async def get_invoice_json(invoices: AsyncGenerator[Invoice, None]) -> AsyncGenerator[str, None]:
    async for invoice in invoices:
        invoice_json = (InvoiceResponse
                        .model_validate(invoice)
                        .model_dump_json())
        yield invoice_json + " \n"
