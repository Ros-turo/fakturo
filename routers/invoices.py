from typing import Annotated

from fastapi import APIRouter, Path, HTTPException, Response
from routers.auth import CurrentUser
from schemas import InvoiceCreate, InvoiceItemCreate, InvoiceResponse, Status
from db_models import Invoice, InvoiceItem
from database import DBSession
from pdf import invoice_pdf



router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.post("/", response_model=InvoiceResponse)
def create_invoice(user: CurrentUser, invoice: InvoiceCreate,
                   db:DBSession):

    uid = user["uid"]
    invoice_db = Invoice(**invoice.model_dump(exclude={"invoice_items"}),
        owner_id=uid
    )
    db.add(invoice_db)
    db.flush()
    for item in invoice.invoice_items:
        item_db = InvoiceItem(**item.model_dump(), invoice_id=invoice_db.id)
        db.add(item_db)
    db.commit()
    db.refresh(invoice_db)
    return invoice_db

@router.get("/", response_model=list[InvoiceResponse])
def get_invoices(user: CurrentUser, db:DBSession):
    uid = user["uid"]
    responses = db.query(Invoice).filter(Invoice.owner_id == uid).all()
    return responses

@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_one_invoice(invoice_id: Annotated[int, Path(ge=0)], user: CurrentUser, db: DBSession):
    uid = user["uid"]
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.owner_id == uid).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Not found")
    return invoice

@router.get("/{invoice_id}/pdf")
def invoice_to_pdf(user: CurrentUser, db: DBSession, invoice_id: int):
    uid = user["uid"]
    invoice = db.query(Invoice).filter( Invoice.id == invoice_id, Invoice.owner_id == uid).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Not found")
    pdf = invoice_pdf(invoice)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=faktura-{invoice.invoice_number}.pdf"}
    )

@router.patch("/{invoice_id}/status", response_model=InvoiceResponse)
def change_status(invoice_id: Annotated[int, Path(ge=0)], user: CurrentUser, db: DBSession,
                  new_status: Status):
    uid = user["uid"]
    invoice = db.query(Invoice).filter(Invoice.owner_id == uid, Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Not found")
    invoice.status = new_status
    db.commit()
    db.refresh(invoice)
    return invoice

