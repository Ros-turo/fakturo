from collections.abc import AsyncGenerator
from typing import Any, Protocol, Sequence

from db_models import Client, Invoice, RefreshToken
from schemas import (
    ClientUpdate,
    InvoiceByStatus,
    InvoiceCreate,
    OrderBy,
    OrderDir,
    Status,
)


class ClientCRUD(Protocol):
    async def get_one_client(self, uid: int, client_id: int) -> Client | None: ...

    async def create_client(self, client: Client) -> Client: ...

    async def update_client(
        self, client: Client, new_value: ClientUpdate
    ) -> Client: ...

    async def delete_client(self, client: Client) -> None: ...


class ClientListing(Protocol):
    async def get_all_clients(self, uid: int) -> list[Client]: ...


class InvoiceCRUD(Protocol):
    async def create_invoice(self, uid: int, invoice: InvoiceCreate) -> Invoice: ...

    async def get_one_invoice(self, uid: int, invoice_id: int) -> Invoice | None: ...

    async def change_invoice_status(
        self, invoice: Invoice, new_status: Status
    ) -> None: ...

    async def delete_invoice(self, invoice: Invoice) -> bool: ...


class InvoiceReporting(Protocol):
    async def get_sum_by_status(self, uid: int) -> list[InvoiceByStatus]: ...

    async def invoice_stats(self, uid: int) -> dict[str, Any]: ...

    async def get_invoices_above_avg(self, uid: int) -> list[Invoice]: ...


class InvoiceListing(Protocol):
    async def get_all_invoices(
        self,
        uid: int,
        client_id: int | None,
        order_by: OrderBy | None,
        order_dir: OrderDir | None,
        status: Status | None,
        limit: int | None,
        offset: int,
    ) -> Sequence[Invoice]: ...

    async def a_get_all_invoices(self, uid: int) -> AsyncGenerator[Invoice, None]:
        raise NotImplementedError
        yield

    async def get_invoices_by_id(
        self, uid: int, invoices_id: set[int]
    ) -> AsyncGenerator[Invoice, None]: ...


class InvoiceBatch(Protocol):
    async def update_overdue_invoices(self, uid: int) -> int: ...


class RefreshTokenWriter(Protocol):
    async def post_refresh_token(self, refresh_token: RefreshToken) -> None: ...
