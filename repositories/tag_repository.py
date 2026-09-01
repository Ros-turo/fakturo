from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from db_models import Tag, Invoice, InvoiceTag
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class TagRepo:

    def __init__(self, db:AsyncSession):
        self.db = db

    async def create_tag(self, name: str, owner_id: int) -> Tag:
        new_tag = Tag(name=name, owner_id=owner_id)
        tag_exist = await self.db.execute(select(Tag).where(Tag.owner_id == owner_id,
                                                            Tag.name == name))
        tag: Tag | None = tag_exist.scalar_one_or_none()
        if not tag:
            self.db.add(new_tag)
            await self.db.commit()
            await self.db.refresh(new_tag)
            return new_tag

        return tag

    async def get_all_tags(self, owner_id: int) -> list[Tag]:
        tags_result = await self.db.execute(select(Tag).where(Tag.owner_id == owner_id))
        tags = tags_result.scalars().all()

        return list(tags)

    async def add_tag_to_invoice(self, invoice_id: int, tag_id: int, uid: int) -> Invoice | None:
        tag_result = await self.db.execute(select(Tag)
                                                .where(Tag.id == tag_id, Tag.owner_id == uid))
        tag = tag_result.scalar_one_or_none()

        invoice_result = await self.db.execute(select(Invoice)
                                               .options(selectinload(Invoice.tags))
                                               .where(Invoice.id == invoice_id))

        invoice = invoice_result.scalar_one_or_none()

        if tag is None or invoice is None:
            return None

        tag_in_invoice = InvoiceTag(invoice_id=invoice_id, tag_id=tag_id)

        self.db.add(tag_in_invoice)
        await self.db.commit()
        return invoice

    async def bulk_upsert_tags(self, tags: list[str], owner_id: int) -> list[Tag]:
        stmt = insert(Tag).values([{"owner_id": owner_id, "name": name} for name in tags])
        stmt = stmt.on_conflict_do_nothing(index_elements=["name","owner_id"])
        await self.db.execute(stmt)
        await self.db.commit()
        return await  self.get_all_tags(owner_id=owner_id)

