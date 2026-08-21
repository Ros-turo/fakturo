import asyncio
import time
from typing import Annotated

from celery import chain
from fastapi import APIRouter, Path, HTTPException, Response, Depends, Query
from starlette.background import BackgroundTasks
from starlette.responses import StreamingResponse, JSONResponse

from routers.auth import CurrentUser, CurrentActiveUser, UserID, SecurityID
from schemas import InvoiceCreate, InvoiceResponse, Status, InvoiceStats, OrderBy, OrderDir, \
    InvoiceListResponse, InvoiceByStatus, BulkPDFResponse
from db_models import Invoice
from logging_config import logger
from repositories.invoice_repository import InvoiceRepo
from database import DBSession, SessionLocal
from pdf import invoice_pdf
from exceptions import InvoiceNotFoundError, InvoiceDeleteError, InvoiceConflict, InvalidStatusChangeError
from celery_app import celery_app, generate_pdf, send_email_task

router = APIRouter(prefix="/invoices", tags=["invoices"])

# Database helper function
def get_invoice_repo(db: DBSession):
    return InvoiceRepo(db)

InvoiceDepends = Annotated[InvoiceRepo, Depends(get_invoice_repo)]

async def invoice_getter(repo:InvoiceDepends, uid: UserID, invoice_id: Annotated[int, Path()]) -> Invoice:
    invoice = await repo.get_one_invoice(uid=uid, invoice_id=invoice_id)
    if not invoice:
        raise InvoiceNotFoundError(invoice_id=invoice_id)
    return invoice

GetterInvoice = Annotated[Invoice, Depends(invoice_getter)]

def draft_invoice_checker(invoice: GetterInvoice):

    if invoice.status == Status.draft:
        return invoice
    raise InvoiceDeleteError("Not allowed to delete invoices that was sent already ")

DraftChecker = Annotated[Invoice, Depends(draft_invoice_checker)]

def valid_status_change(old_status: Status, new_status: Status):

    if ((old_status == Status.paid) or (old_status == Status.overdue and new_status == Status.draft) or
            (old_status == Status.sent and new_status == Status.draft)):
        raise InvalidStatusChangeError(from_status=old_status, to_status=new_status)

# Background tasks

def notify_invoice_created(invoice_number):
    try:
        time.sleep(2)
        logger.info(f"Invoice {invoice_number} was created")
    except Exception as e:
        logger.exception(e)

# Functions-helpers

async def get_invoice_json(invoices):
    async for invoice in invoices:
        invoice_json = (InvoiceResponse
                        .model_validate(invoice)
                        .model_dump_json())
        yield invoice_json + " \n"

@router.post("/create_invoice", response_model=InvoiceResponse)
async def create_invoice(user: CurrentUser, invoice_data: InvoiceCreate,
                   repo:InvoiceDepends, background_task: BackgroundTasks):

    uid = user["uid"]
    new_invoice = await repo.create_invoice(uid=uid, invoice=invoice_data)
    background_task.add_task(notify_invoice_created, new_invoice.invoice_number)
    return new_invoice

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
async def get_invoices_stats(uid: UserID, repo:InvoiceDepends):
    return await repo.invoice_stats(uid=uid)


@router.get("/sum_by_status", response_model=list[InvoiceByStatus])
async def sum_by_status(uid: UserID, repo:InvoiceDepends)->list[InvoiceByStatus]:
    result = await repo.get_sum_by_status(uid=uid)
    return result

@router.get("/update_overdue")
async def update_overdue(uid: UserID, repo: InvoiceDepends):
    result = await repo.update_overdue_invoices(uid=uid)
    return result

@router.get("/export_invoices")
async def export_invoices(uid: UserID, repo: InvoiceDepends):
    result = repo.a_get_all_invoices(uid=uid)
    return StreamingResponse(get_invoice_json(result), media_type="application/x-ndjson")

@router.get("/invoices_dashboard")
async def invoice_dashboard(uid: UserID):
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

@router.get("/bulk_pdf_create", response_model= BulkPDFResponse)
async def bulk_invoice_to_pdf(invoices_id: Annotated[set[int], Query(min_length=1, max_length=50)],
                              uid: UserID, repo: InvoiceDepends):
    tripped_id = set()
    coros = []
    invoice_generator = repo.get_invoices_by_id(uid, invoices_id)
    async for invoice in invoice_generator:
            tripped_id.add(invoice.id)
            coro = asyncio.to_thread(invoice_pdf, invoice)
            coros.append(coro)

    pdf_list = await asyncio.gather(*coros, return_exceptions=True)

    invoices_id -= tripped_id

    if invoices_id:
        logger.warning(f"User {uid} attempted to access invoices not owned: {invoices_id}")

    size = sum([len(pdf) for pdf in pdf_list if not isinstance(pdf, BaseException)])
    created_count = len(tripped_id) - len([pdf for pdf in pdf_list if isinstance(pdf, BaseException)])
    return {
        "status": "ok",
        "Denied_id": invoices_id,
        "Created_pdf_count":created_count,
        "Size": size,
    }

@router.get("/average_total_amount")
async def get_invoices_above_average(user: CurrentActiveUser, invoice_repo: InvoiceDepends):

    uid = user["uid"]

    invoices = await invoice_repo.get_invoices_above_avg(uid=uid)

    return invoices

@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_one_invoice(invoice: GetterInvoice):
    return invoice

@router.post("/{invoice_id}/pdf")
async def invoice_to_pdf(uid: UserID, invoice_id: Annotated[int, Path()]):
    """ Convert invoice to pdf"""

    pdf_email_workflow = chain(
        generate_pdf.s(invoice_id, uid),
        send_email_task.s(text="Your invoice in pdf is coming")
    )

    pdf_email_workflow.apply_async()

    return JSONResponse(status_code=202,
                        content={
                            "Message": "We work on your task, it will be take a few minutes to complete your task",
                        })

@router.patch("/{invoice_id}/status", response_model=InvoiceResponse)
async def change_status(invoice: GetterInvoice, user: CurrentActiveUser,
                        new_status: Status, repo: InvoiceDepends):
    old_status = invoice.status
    valid_status_change(old_status=old_status, new_status=new_status)

    await repo.change_invoice_status(invoice=invoice, new_status=new_status)
    return invoice


@router.delete("/{invoice_id}")
async def delete_draft_invoice(s_uid: SecurityID, invoice: DraftChecker,
                                  invoice_repo: InvoiceDepends):

    result = await invoice_repo.delete_invoice(invoice)

    if result:
        logger.warning(f"Invoice {invoice.id =} {invoice.invoice_number= } was deleted suspicious")
        raise InvoiceConflict("Invoice was already deleted, if it's wasn't you please change a password and contact us to help")

    return JSONResponse(
        status_code=200,
        content = {"detail": " Invoice is deleted"}
    )


