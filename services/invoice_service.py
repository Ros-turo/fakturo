from typing import AsyncGenerator, cast

from celery import chain

from db_models import Invoice
from exceptions import (
    InvoiceConflict,
    InvoiceDeleteError,
    InvalidStatusChangeError,
    InvoiceNotFoundError,
)
from logging_config import logger
from repositories.interfaces import InvoiceCRUD
from schemas import Status, STATUS_MAP, InvoiceResponse


def draft_invoice_checker(invoice: Invoice) -> None:
    if invoice.status != Status.draft:
        raise InvoiceDeleteError("Not allowed to delete invoices that was sent already ")


async def delete_invoice_with_checker(
        invoice: Invoice,
        invoice_repo: InvoiceCRUD
) -> None:
    draft_invoice_checker(invoice=invoice)
    result = await invoice_repo.delete_invoice(invoice=invoice)
    if result:
        logger.warning(
            f"Invoice {invoice.id =} {invoice.invoice_number= } was deleted suspicious"
        )
        raise InvoiceConflict(
            "Invoice was already deleted, if it's wasn't you please change a password "
            "and contact us to help"
        )


def valid_status_change(old_status: Status, new_status: Status) -> None:
    if not (new_status in STATUS_MAP[old_status]):
        raise InvalidStatusChangeError(from_status=old_status, to_status=new_status)


async def status_change_with_checker(
        invoice: Invoice,
        new_status: Status,
        invoice_repo: InvoiceCRUD
) -> None:

    valid_status_change(old_status=invoice.status, new_status=new_status)
    await invoice_repo.change_invoice_status(invoice=invoice, new_status=new_status)


async def get_invoice_json(invoices: AsyncGenerator[Invoice, None]) -> AsyncGenerator[str, None]:
    async for invoice in invoices:
        invoice_json = (InvoiceResponse
                        .model_validate(invoice)
                        .model_dump_json())
        yield invoice_json + " \n"
