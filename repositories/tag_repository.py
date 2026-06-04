from sqlalchemy.orm import selectinload

from db_models import Tag, Invoice
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class TagRepo:

    def __init__(self, db:AsyncSession):
        self.db = db

    async def create_tag(self, name: str, owner_id: int) -> Tag:
        new_tag = Tag(name=name, owner_id=owner_id)
        tag_exist = await self.db.execute(select(Tag).where(Tag.owner_id == owner_id,
                                                            Tag.name == name))
        tag: Tag = tag_exist.scalar_one_or_none()
        if not tag:
            self.db.add(new_tag)
            await self.db.commit()
            await self.db.refresh(new_tag)
            return new_tag

        return tag

    async def get_all_tags(self, owner_id: int) -> list[Tag]:
        tags_result = await self.db.execute(select(Tag).where(Tag.owner_id == owner_id))
        tags = tags_result.scalars().all()

        return tags

    async def add_tag_to_invoice(self, invoice_id: int, tag_id: int, uid: int) -> Invoice | None:
        tag_result = await self.db.execute(select(Tag)
                                           .where(Tag.id == tag_id, Tag.owner_id == uid))
        tag: Tag = tag_result.scalar_one_or_none()

        if not tag:
            return None

        invoice_result = await self.db.execute(select(Invoice)
                                       .options(selectinload(Invoice.tags))
                                       .where(Invoice.id == invoice_id))
        invoice: Invoice = invoice_result.scalar_one_or_none()

        if not invoice:
            return None

        invoice.tags.append(tag)
        await self.db.commit()
        return invoice