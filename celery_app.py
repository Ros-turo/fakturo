import asyncio

from celery import Celery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import joinedload, selectinload

from db_models import Invoice
from settings import settings
from pdf import invoice_pdf
from exceptions import InvoiceNotFound

celery_app = Celery(
    'celery_fakturo',
    broker = f'redis://{settings.redis_host}:{settings.redis_port}/1',
    backend= f'redis://{settings.redis_host}:{settings.redis_port}/2'
)

@celery_app.task(autoretry_for=(ConnectionError,), max_retries=3, retry_backoff=True)
def send_email_task(result: list[bytes|str], text:str ):

    pdf_bytes, email = result
    print(pdf_bytes, email, text)

@celery_app.task(autoretry_for=(ConnectionError,), max_retries=3, retry_backoff=True)
def generate_pdf(invoice_id: int, uid: int):

    invoice = asyncio.run(_get_invoice_async(invoice_id, uid))

    if invoice is None:
        raise InvoiceNotFound(invoice_id=invoice_id, uid=uid) # Placeholder if invoice not exist, message user

    email = invoice.owner.email
    pdf = invoice_pdf(invoice)

    result = [pdf, email]
    return result





async def _get_invoice_async(invoice_id: int, uid: int):
    engine = create_async_engine(url=settings.db_url)
    try:
        async with AsyncSession(engine) as db:

            stmt = select(Invoice).where(Invoice.id == invoice_id, Invoice.owner_id == uid).options(
                selectinload(Invoice.invoice_items),
                joinedload(Invoice.owner),
                joinedload(Invoice.client)
            )

            invoice = await db.execute(stmt)

            return invoice.scalar_one_or_none()
    finally:
        await engine.dispose()
