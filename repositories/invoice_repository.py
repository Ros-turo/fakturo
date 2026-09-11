from datetime import date
from typing import Any, Generator, AsyncGenerator, Sequence

from sqlalchemy import RowMapping, Select, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from db_models import AuditLog, Invoice, InvoiceItem
from repositories.base_repository import BaseRepo
from schemas import Action, InvoiceByStatus, InvoiceCreate, OrderBy, OrderDir, Status

INVOICE_EAGER_OPTIONS = (
    selectinload(Invoice.invoice_items),
    selectinload(Invoice.owner),
    selectinload(Invoice.client),
    selectinload(Invoice.tags)
)


class InvoiceRepo(BaseRepo):

    @staticmethod
    def filtering(
            stmt: Select[Invoice],
            client_id: int | None,
            status: Status | None,
    ) -> Select[Invoice]:


        if not client_id is None:
            stmt = stmt.where(Invoice.client_id == client_id)
        if not status is None:
            stmt = stmt.where(Invoice.status == status)
        return stmt

    @staticmethod
    def pagination(
            stmt: Select[Invoice],
            limit: int | None,
            offset: int
    ) -> Select[Invoice]:

        if not limit is None:
            stmt = stmt.limit(limit)
        return stmt.offset(offset)

    @staticmethod
    def order_by_logic(
            stmt: Select[Invoice],
            order_by: OrderBy | None,
            order_dir: OrderDir | None,
    ) -> Select[Invoice]:

        if not order_by is None:
            order = getattr(Invoice, order_by.value)
            if not order_dir is None:
                order = getattr(order, order_dir.value)()
            stmt = stmt.order_by(order)
        else:
            stmt = stmt.order_by(Invoice.id.asc())

        return stmt

    async def _invoice_exist_checker(self, invoice: Invoice) -> bool:

        checker = await self.db.get(Invoice, invoice.id)
        return checker is not None

    async def create_invoice(self, uid:int, invoice: InvoiceCreate) -> Invoice:

        total_amount = sum(item.total_with_vat for item in invoice.invoice_items) # rewrite to metod
        invoice_in_db = Invoice(**invoice.model_dump(exclude={"invoice_items"}), owner_id = uid,
                                total_amount=total_amount)
        self.db.add(invoice_in_db)
        await self.db.flush()

        await self.db.execute(insert(InvoiceItem)
                              .values([{"invoice_id": invoice_in_db.id,
                                                     **item.model_dump(exclude={"subtotal", "total_with_vat"})}
                                                    for item in invoice.invoice_items])) #SRP - creating a ivnoiceitems-> invoiceitem repo
        await self.db.commit()
        result = await self.db.execute(select(Invoice)
                                       .options(selectinload(Invoice.invoice_items))
                                       .where(Invoice.id == invoice_in_db.id))
        return result.scalar_one() # Create and get invoice? SRP problem?

    async def get_all_invoices(
            self,
            uid:int,
            client_id: int | None,
            order_by: OrderBy | None,
            order_dir: OrderDir | None,
            status: Status | None,
            limit: int | None,
            offset:int
    ) -> Sequence[Invoice]: # too much argument
        # -> new class? or classes? Separate to filter_where logic(client_id, status), pagination(limit, offset) and order_logic(order_by, order_dir)

        stmt = (select(Invoice).options(selectinload(Invoice.invoice_items)).where(Invoice.owner_id == uid))
        stmt = self.filtering(stmt, client_id, status)
        stmt = self.pagination(stmt, limit, offset)
        stmt = self.order_by_logic(stmt, order_by, order_dir)

        raw_result = await self.db.execute(stmt)
        result = raw_result.scalars().all()

        return result

    async def a_get_all_invoices(self, uid: int) -> AsyncGenerator[Invoice, None]:
        result = await self.db.stream(select(Invoice).where(Invoice.owner_id == uid).options(*INVOICE_EAGER_OPTIONS))
        invoices = result.scalars()
        async for invoice in invoices:
            yield invoice

    async def get_one_invoice(self, uid:int, invoice_id:int) -> Invoice | None:
        invoice_result = await self.db.execute(
            select(Invoice)
            .options(*INVOICE_EAGER_OPTIONS)
            .where(
                Invoice.id == invoice_id,
                Invoice.owner_id == uid
            )
        )
        invoice = invoice_result.scalar_one_or_none()
        return invoice

    async def get_invoices_by_id(self,uid: int ,invoices_id: set[int]) -> AsyncGenerator[Invoice, None]:
        stmt =(select(Invoice)
            .where(Invoice.owner_id == uid, Invoice.id.in_(invoices_id))
            .options(*INVOICE_EAGER_OPTIONS))
        invoices = await self.db.stream(stmt)
        result = invoices.scalars()
        async for invoice in result:
            yield invoice

    async def change_invoice_status(self, invoice: Invoice, new_status: Status) -> None:
        new_log= AuditLog(
            table_name=invoice.__tablename__,
            row_id=invoice.id,
            action=Action.update,
            old_value=str(invoice.status),
            new_value=str(new_status)# SRP create AuditLog instance not a Invoicerepo responsability
        )
        self.db.add(new_log)
        invoice.status = new_status
        self.db.add(invoice)
        await self.db.commit()

    async def get_sum_by_status(self, uid:int) -> list[RowMapping]:
        raw_result = await self.db.execute(
            select(
                Invoice.status,
                func.count(Invoice.id).label("count"),
                func.sum(Invoice.total_amount).label("total"))
            .where(Invoice.owner_id == uid)
            .group_by(Invoice.status))
        result = list(raw_result.mappings().all())

        return result

    async def update_overdue_invoices(self,uid:int) -> int:
        # Wrong DRY - need a method which only get a overdue invoices, without updates...
        stmt = (update(Invoice)
                .where(Invoice.owner_id == uid,
                       Invoice.due_date < date.today(),
                       Invoice.status == Status.sent)
                .values(status = Status.overdue))
        result = await self.db.execute(stmt)
        await self.db.commit()
        return int(result.rowcount) # type: ignore [attr-defined]

    async def invoice_stats(self, uid:int) -> dict[str, Any] :
        # CQS problem
        overdue_row = await self.update_overdue_invoices(uid=uid) # Not safety, SRP problem
        main_stmt = (
            select(func.count(Invoice.id).label("total_invoices"),
                   func.sum(Invoice.total_amount).label("total_revenue")
                   )
            .where(Invoice.owner_id == uid)
        )

        sub_stmt = await self.get_sum_by_status(uid) # DRY_2 get_sum_by_status returned value(almost)
        main_result = await self.db.execute(main_stmt)
        main_row = main_result.one()

        return {
            "total_invoices": main_row.total_invoices,
            "total_revenue": main_row.total_revenue,
            "by_status":[invoice for invoice in sub_stmt],
            "overdue_updated": overdue_row
        }

    async def get_invoices_above_avg(self, uid) -> list[Invoice]:

        sub_query = (select(func.avg(Invoice.total_amount)).where(Invoice.owner_id == uid)).scalar_subquery()

        stmt = select(Invoice).where(Invoice.total_amount > sub_query, Invoice.owner_id == uid)

        row_result = await self.db.execute(stmt)

        result = list(row_result.scalars().all())
        return result

    async def delete_invoice(self, invoice) -> bool:

        await self.db.delete(invoice)
        await self.db.commit()

        return await self._invoice_exist_checker(invoice)
