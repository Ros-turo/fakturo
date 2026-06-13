from datetime import date
from decimal import Decimal

from sqlalchemy import select, func, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from db_models import Invoice, InvoiceItem, AuditLog
from schemas import InvoiceCreate, Status, Action
from sqlalchemy.ext.asyncio import AsyncSession

class InvoiceRepo:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_invoice(self, uid:int, invoice: InvoiceCreate) -> Invoice:
        total_amount = sum((item.unit_price*item.quantity) * Decimal(1 + (item.vat_rate / 100)) for item in invoice.invoice_items)
        invoice_in_db = Invoice(**invoice.model_dump(exclude={"invoice_items"}), owner_id = uid,
                                total_amount=total_amount)
        self.db.add(invoice_in_db)
        await self.db.flush()

        await self.db.execute(insert(InvoiceItem)
                              .values([{"invoice_id": invoice_in_db.id,
                                                     **item.model_dump()}
                                                    for item in invoice.invoice_items]))
        await self.db.commit()
        result = await self.db.execute(select(Invoice)
                                       .options(selectinload(Invoice.invoice_items))
                                       .where(Invoice.id == invoice_in_db.id))
        return result.scalar_one()

    async def get_all_invoices(self, uid:int) -> list[Invoice]:
        invoices_result = await self.db.execute(select(Invoice)
                                                .options(selectinload(Invoice.invoice_items))
                                                .where(Invoice.owner_id == uid))
        return invoices_result.scalars().all()

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

    async def get_invoice_summary(self, uid:int):
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
