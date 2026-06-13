from typing import Annotated

from fastapi import APIRouter, Path, HTTPException, Response, Depends
from routers.auth import CurrentUser
from schemas import InvoiceCreate, InvoiceItemCreate, InvoiceResponse, Status, InvoiceStats
from db_models import Invoice, InvoiceItem
from repositories.invoice_repository import InvoiceRepo
from database import DBSession
from pdf import invoice_pdf



router = APIRouter(prefix="/invoices", tags=["invoices"])

def get_invoice_repo(db: DBSession):
    return InvoiceRepo(db)

InvoiceDepends = Annotated[InvoiceRepo, Depends(get_invoice_repo)]

@router.post("/", response_model=InvoiceResponse)
async def create_invoice(user: CurrentUser, invoice: InvoiceCreate,
                   repo:InvoiceDepends):

    uid = user["uid"]
    return await repo.create_invoice(uid=uid, invoice=invoice)

@router.get("/", response_model=list[InvoiceResponse])
async def get_invoices(user: CurrentUser, repo: InvoiceDepends):
    uid = user["uid"]
    responses = await repo.get_all_invoices(uid=uid)
    return responses

@router.get("/stats", response_model=InvoiceStats)
async def get_invoices_stats(user:CurrentUser, repo:InvoiceDepends):
    uid = user["uid"]
    return await repo.invoice_stats(uid=uid)


@router.get("/total_sum")
async def total_sum_of_invoices(user: CurrentUser, repo:InvoiceDepends):
    uid = user["uid"]
    result = await repo.get_invoice_summary(uid=uid)
    return result

@router.get("/update_overdue")
async def update_overdue(user: CurrentUser, repo: InvoiceDepends):
    uid = user["uid"]
    result = await repo.update_overdue_invoices(uid=uid)
    return result

@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_one_invoice(invoice_id: Annotated[int, Path(ge=0)],
                          user: CurrentUser, repo: InvoiceDepends):
    uid = user["uid"]
    invoice = await repo.get_one_invoice(uid=uid, invoice_id=invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Not found")
    return invoice

@router.get("/{invoice_id}/pdf")
async def invoice_to_pdf(user: CurrentUser, invoice_id: int,
                   repo: InvoiceDepends):
    uid = user["uid"]
    invoice = await repo.get_one_invoice(uid=uid, invoice_id=invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Not found")
    pdf = invoice_pdf(invoice)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=faktura-{invoice.invoice_number}.pdf"}
    )

@router.patch("/{invoice_id}/status", response_model=InvoiceResponse)
async def change_status(invoice_id: Annotated[int, Path(ge=0)], user: CurrentUser,
                  new_status: Status, repo: InvoiceDepends):
    uid = user["uid"]
    invoice = await repo.get_one_invoice(uid=uid, invoice_id=invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Not found")
    await repo.change_invoice_status(invoice=invoice, new_status=new_status)
    return await repo.get_one_invoice(uid=uid, invoice_id=invoice_id)


