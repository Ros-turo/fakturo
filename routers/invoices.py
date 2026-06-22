import asyncio
from typing import Annotated

from fastapi import APIRouter, Path, HTTPException, Response, Depends, Query
from starlette.responses import StreamingResponse

from routers.auth import CurrentUser, CurrentActiveUser
from schemas import InvoiceCreate, InvoiceItemCreate, InvoiceResponse, Status, InvoiceStats, OrderBy, OrderDir, \
    InvoiceListResponse, InvoiceByStatus
from db_models import Invoice, InvoiceItem
from repositories.invoice_repository import InvoiceRepo
from database import DBSession, SessionLocal
from pdf import invoice_pdf



router = APIRouter(prefix="/invoices", tags=["invoices"])

def get_invoice_repo(db: DBSession):
    return InvoiceRepo(db)

InvoiceDepends = Annotated[InvoiceRepo, Depends(get_invoice_repo)]

async def get_invoice_json(invoices):
    async for invoice in invoices:
        invoice_json = (InvoiceResponse
                        .model_validate(invoice)
                        .model_dump_json())
        yield invoice_json + " \n"

@router.post("/", response_model=InvoiceResponse)
async def create_invoice(user: CurrentUser, invoice: InvoiceCreate,
                   repo:InvoiceDepends):

    uid = user["uid"]
    return await repo.create_invoice(uid=uid, invoice=invoice)

@router.get("/", response_model=InvoiceListResponse)
async def get_invoices(user: CurrentUser, repo: InvoiceDepends,
                       client_id: Annotated[int | None, Query()] = None,
                       order_by: Annotated[OrderBy | None, Query()] = None,
                       order_dir: Annotated[OrderDir | None, Query()] = None,
                       status: Annotated[Status | None, Query()] = None,
                       limit: Annotated[int | None, Query(gt=0)] = None,
                       offset: Annotated[int, Query()] = 0
                       ):
    uid = user["uid"]
    responses = await repo.get_all_invoices(uid=uid,
                                            client_id=client_id,
                                            order_by=order_by,
                                            order_dir=order_dir,
                                            status=status,
                                            limit=limit,
                                            offset=offset)
    return responses

@router.get("/stats", response_model=InvoiceStats)
async def get_invoices_stats(user:CurrentUser, repo:InvoiceDepends):
    uid = user["uid"]
    return await repo.invoice_stats(uid=uid)


@router.get("/sum_by_status", response_model=list[InvoiceByStatus])
async def sum_by_status(user: CurrentUser, repo:InvoiceDepends)->list[InvoiceByStatus]:
    uid = user["uid"]
    result = await repo.get_sum_by_status(uid=uid)
    return result

@router.get("/update_overdue")
async def update_overdue(user: CurrentUser, repo: InvoiceDepends):
    uid = user["uid"]
    result = await repo.update_overdue_invoices(uid=uid)
    return result

@router.get("/export_invoices")
async def export_invoices(user: CurrentUser, repo: InvoiceDepends):
    uid = user["uid"]
    result = repo.a_get_all_invoices(uid=uid)
    return StreamingResponse(get_invoice_json(result), media_type="application/x-ndjson")

@router.get("/invoices_dashboard")
async def invoice_dashboard(user: CurrentUser):
    uid = user["uid"]
    async with SessionLocal() as session_1, SessionLocal() as session_2:
        repo_1 = get_invoice_repo(session_1)
        repo_2 = get_invoice_repo(session_2)
        async with asyncio.TaskGroup() as tg:
            sum_by_status_result = tg.create_task(repo_1.get_sum_by_status(uid=uid))
            stats_result = tg.create_task(repo_2.invoice_stats(uid=uid))
    return {
        "sum_by_status": sum_by_status_result.result(),
        "stats": stats_result.result()
    }

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
    """ Convert invoice to pdf"""
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
async def change_status(invoice_id: Annotated[int, Path(ge=0)], user: CurrentActiveUser,
                  new_status: Status, repo: InvoiceDepends):
    uid = user["uid"]
    invoice = await repo.get_one_invoice(uid=uid, invoice_id=invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Not found")
    await repo.change_invoice_status(invoice=invoice, new_status=new_status)
    return await repo.get_one_invoice(uid=uid, invoice_id=invoice_id)


