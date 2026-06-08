from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db_models import Invoice, InvoiceItem
from schemas import InvoiceCreate, Status
from sqlalchemy.ext.asyncio import AsyncSession

class InvoiceRepo:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_invoice(self, uid, invoice: InvoiceCreate) -> Invoice:
        invoice_in_db = Invoice(**invoice.model_dump(exclude={"invoice_items"}), owner_id = uid)
        self.db.add(invoice_in_db)
        await self.db.flush()

        for item in invoice.invoice_items:
            item_in_db = InvoiceItem(**item.model_dump(), invoice_id=invoice_in_db.id)
            self.db.add(item_in_db)
        await self.db.commit()
        result = await self.db.execute(select(Invoice)
                                       .options(selectinload(Invoice.invoice_items))
                                       .where(Invoice.id == invoice_in_db.id))
        return result.scalar_one()

    async def get_all_invoices(self, uid) -> list[Invoice]:
        invoices_result = await self.db.execute(select(Invoice)
                                                .options(selectinload(Invoice.invoice_items))
                                                .where(Invoice.owner_id == uid))
        return invoices_result.scalars().all()

    async def get_one_invoice(self, uid, invoice_id) -> Invoice | None:
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
        invoice.status = new_status
        self.db.add(invoice)
        await self.db.commit()
