from datetime import date
from decimal import Decimal

from sqlalchemy import select, func, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from db_models import Invoice, InvoiceItem, AuditLog
from schemas import InvoiceCreate, Status, Action, OrderBy, OrderDir
from sqlalchemy.ext.asyncio import AsyncSession

class InvoiceRepo:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _invoice_exist_checker(self, invoice: Invoice) -> bool:

        checker = await self.db.get(Invoice, invoice.id)
        return checker is not None

    async def create_invoice(self, uid:int, invoice: InvoiceCreate) -> Invoice:
        total_amount = sum(item.total_with_vat for item in invoice.invoice_items)
        invoice_in_db = Invoice(**invoice.model_dump(exclude={"invoice_items"}), owner_id = uid,
                                total_amount=total_amount)
        self.db.add(invoice_in_db)
        await self.db.flush()

        await self.db.execute(insert(InvoiceItem)
                              .values([{"invoice_id": invoice_in_db.id,
                                                     **item.model_dump(exclude={"subtotal", "total_with_vat"})}
                                                    for item in invoice.invoice_items]))
        await self.db.commit()
        result = await self.db.execute(select(Invoice)
                                       .options(selectinload(Invoice.invoice_items))
                                       .where(Invoice.id == invoice_in_db.id))
        return result.scalar_one()

    async def get_all_invoices(self, uid:int, client_id: int | None = None,
                               order_by: OrderBy | None = None, order_dir: OrderDir | None = None,
                               status: Status | None = None, limit: int | None = None, offset:int = 0) -> dict:
        items_stmt =(select(Invoice)
               .options(selectinload(Invoice.invoice_items))
               .where(Invoice.owner_id == uid)
               .offset(offset)
                     )

        count_stmt =(select(func.count(Invoice.id))
               .where(Invoice.owner_id == uid)
               )
        filters = []

        if not client_id is None:
            filters.append(Invoice.client_id == client_id)

        if not status is None:
            filters.append(Invoice.status == status.value)

        count_stmt = count_stmt.where(*filters)
        count_result = await self.db.execute(count_stmt)

        if not order_by is None:
            order = getattr(Invoice, order_by.value)
            if not order_dir is None:
                order = getattr(order, order_dir.value)()
            items_stmt = items_stmt.order_by(order)
        else:
            items_stmt = items_stmt.order_by(Invoice.id.asc())

        if not limit is None:
            items_stmt = items_stmt.limit(limit)

        items_stmt = items_stmt.where(*filters)
        invoices_items_result = await self.db.execute(items_stmt)

        return {
            "total": count_result.scalar_one_or_none(),
            "items": invoices_items_result.scalars().all()
        }

    async def a_get_all_invoices(self, uid: int):
        result = await self.db.stream(select(Invoice).where(Invoice.owner_id == uid)
                                      .options(selectinload(Invoice.invoice_items),
                                               selectinload(Invoice.owner),
                                               selectinload(Invoice.client),
                                               selectinload(Invoice.tags)))
        invoices = result.scalars()
        async for invoice in invoices:
            yield invoice

    async def get_one_invoice(self, uid:int, invoice_id:int) -> Invoice | None:
        invoice_result = await self.db.execute(select(Invoice)
                                               .options(selectinload(Invoice.invoice_items),
                                                        selectinload(Invoice.owner),
                                                        selectinload(Invoice.client),
                                                        selectinload(Invoice.tags))
                                               .where(Invoice.id == invoice_id,
                                                      Invoice.owner_id == uid))
        invoice = invoice_result.scalar_one_or_none()
        return invoice

    async def get_invoices_by_id(self,uid: int ,invoices_id: set[int]):
        stmt =(select(Invoice)
            .where(Invoice.owner_id == uid,
                Invoice.id.in_(invoices_id))
            .options(
                    selectinload(Invoice.invoice_items),
                    selectinload(Invoice.owner),
                    selectinload(Invoice.client),
                    selectinload(Invoice.tags)))
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
            new_value=str(new_status)
        )
        self.db.add(new_log)
        invoice.status = new_status
        self.db.add(invoice)
        await self.db.commit()

    async def get_sum_by_status(self, uid:int):
        result = await self.db.execute(select(Invoice.status,
                                              func.count(Invoice.id).label("count"),
                                              func.sum(Invoice.total_amount).label("total"))
                                       .where(Invoice.owner_id == uid)
                                       .group_by(Invoice.status))
        return [row._asdict() for row in result.all()]

    async def update_overdue_invoices(self,uid:int):
        stmt = (update(Invoice)
                .where(Invoice.owner_id == uid,
                       Invoice.due_date < date.today(),
                       Invoice.status == Status.sent)
                .values(status = Status.overdue))
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def invoice_stats(self, uid:int):
        overdue_row = await self.update_overdue_invoices(uid=uid)
        main_stmt = (
            select(func.count(Invoice.id).label("total_invoices"),
                   func.sum(Invoice.total_amount).label("total_revenue")
                   )
            .where(Invoice.owner_id == uid)
        )

        sub_stmt = (
            select(Invoice.status,
                   func.count(Invoice.status).label("count"),
                   func.sum(Invoice.total_amount).label("total")
                   )
            .where(Invoice.owner_id == uid)
            .group_by(Invoice.status)
        )
        main_result = await self.db.execute(main_stmt)
        main_row = main_result.one()
        sub_result = await self.db.execute(sub_stmt)

        return {
            "total_invoices": main_row.total_invoices,
            "total_revenue": main_row.total_revenue,
            "by_status":[row._asdict() for row in sub_result.all()],
            "overdue_updated": overdue_row
        }

    async def get_invoices_above_avg(self, uid):

        sub_query = (select(func.avg(Invoice.total_amount)).where(Invoice.owner_id == uid)).scalar_subquery()

        stmt = select(Invoice).where(Invoice.total_amount > sub_query, Invoice.owner_id == uid)

        result = await self.db.execute(stmt)


        return result.scalars().all()

    async def delete_invoice(self, invoice) -> bool:

        await self.db.delete(invoice)
        await self.db.commit()

        return await self._invoice_exist_checker(invoice)
