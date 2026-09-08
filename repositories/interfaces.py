from typing import Any, AsyncGenerator, Protocol

from db_models import Invoice
from schemas import InvoiceCreate, Status, InvoiceByStatus, OrderBy, OrderDir


class InvoiceCRUD(Protocol):

    async def create_invoice(self, uid:int, invoice: InvoiceCreate) -> Invoice: ...

    async def get_one_invoice(self, uid:int, invoice_id: int) -> Invoice | None: ...

    async def change_invoice_status(self, invoice: Invoice, new_status: Status) -> None: ...

    async def delete_invoice(self, invoice: Invoice) -> bool: ...


class InvoiceReporting(Protocol):

    async def get_sum_by_status(self, uid: int) -> list[InvoiceByStatus]: ...

    async def invoice_stats(self, uid: int) -> dict[str, Any]: ...

    async def get_invoices_above_avg(self, uid) -> list[Invoice]: ...


class InvoiceListing(Protocol):

    async def get_all_invoices(self, uid: int, client_id: int | None = None,
                               order_by: OrderBy | None = None, order_dir: OrderDir | None = None,
                               status: Status | None = None, limit: int | None = None,
                               offset: int = 0) -> dict[str, Any]: ...

    async def a_get_all_invoices(self, uid: int) -> AsyncGenerator[Invoice, None]: ...

    async def get_invoices_by_id(self, uid: int, invoices_id: set[int]) -> AsyncGenerator[Invoice, None]: ...


class InvoiceBatch(Protocol):

    async def update_overdue_invoices(self,uid:int) -> int: ...