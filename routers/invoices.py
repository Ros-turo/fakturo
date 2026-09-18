import asyncio
from typing import Annotated, Any, Sequence
from celery import chain
from fastapi import APIRouter, Depends, Path, Query, status
from starlette.responses import JSONResponse, StreamingResponse

from celery_app import generate_pdf, send_email_task
from database import DBSession, SessionLocal
from db_models import Invoice
from exceptions import (
    InvoiceConflict,
    InvoiceNotFoundError,
)
from logging_config import logger
from repositories.interfaces import (
    InvoiceCRUD,
    InvoiceListing,
    InvoiceReporting,
    InvoiceBatch,
)
from repositories.invoice_repository import InvoiceRepo
from routers.auth import UserID, get_current_user, get_current_user_active
from routers.clients import ClientCRUDDepends, client_getter
from schemas import (
    InvoiceByStatus,
    InvoiceCreate,
    InvoiceResponse,
    InvoiceStats,
    OrderBy,
    OrderDir,
    OrderQuery,
    PaginationQuery,
    Status,
)
from services.invoice_service import (
    draft_invoice_checker,
    valid_status_change,
    get_invoice_json,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


# Database helper function
def get_invoice_repo(db: DBSession) -> InvoiceRepo:
    return InvoiceRepo(db)


InvoiceCRUDDepends = Annotated[InvoiceCRUD, Depends(get_invoice_repo)]
InvoiceReportingDepends = Annotated[InvoiceReporting, Depends(get_invoice_repo)]
InvoiceListingDepends = Annotated[InvoiceListing, Depends(get_invoice_repo)]
InvoiceBatchDepends = Annotated[InvoiceBatch, Depends(get_invoice_repo)]


async def is_user_has_client(client_repo: ClientCRUDDepends, uid: UserID, invoice_data: InvoiceCreate) -> bool:
    client_id = invoice_data.client_id
    await client_getter(client_id=client_id, client_repo=client_repo, uid=uid)
    return True


async def invoice_getter(repo: InvoiceCRUDDepends, uid: UserID, invoice_id: Annotated[int, Path()]) -> Invoice:
    invoice = await repo.get_one_invoice(uid=uid, invoice_id=invoice_id)
    if not invoice:
        raise InvoiceNotFoundError(invoice_id=invoice_id)
    return invoice


GetterInvoice = Annotated[Invoice, Depends(invoice_getter)]
DraftChecker = Annotated[Invoice, Depends(draft_invoice_checker)]  # Checking if invoice has draft status


# Query helpers
def pagination_query(
        limit: Annotated[int | None, Query()] = None,
        offset: Annotated[int, Query()] = 0
) -> PaginationQuery:
    return PaginationQuery(limit=limit, offset=offset)


PagDepends = Annotated[PaginationQuery, Depends(pagination_query)]


def order_query(
        order_by: Annotated[OrderBy | None, Query()] = None,
        order_dir: Annotated[OrderDir | None, Query()] = None,
) -> OrderQuery:
    return OrderQuery(order_by=order_by, order_dir=order_dir)


OrderQueryDepends = Annotated[OrderQuery, Depends(order_query)]


@router.post("/create_invoice", status_code=status.HTTP_201_CREATED, response_model=InvoiceResponse,
             dependencies=[Depends(is_user_has_client)])
async def create_invoice(
        uid: UserID,
        invoice_data: InvoiceCreate,
        invoice_repo: InvoiceCRUDDepends,
) -> Invoice:
    new_invoice = await invoice_repo.create_invoice(uid=uid, invoice=invoice_data)
    return new_invoice


@router.get("/", status_code=status.HTTP_200_OK, response_model=Sequence[InvoiceResponse])
async def get_invoices(
        uid: UserID,
        invoice_repo: InvoiceListingDepends,
        pagination: PagDepends,
        order: OrderQueryDepends,
        client_id: Annotated[int | None, Query()] = None,
        status: Annotated[Status | None, Query()] = None,
):
    responses = await invoice_repo.get_all_invoices(uid=uid,
                                                    client_id=client_id,
                                                    order_by=order.order_by,
                                                    order_dir=order.order_dir,
                                                    status=status,
                                                    limit=pagination.limit,
                                                    offset=pagination.offset)
    return responses


@router.get("/stats", status_code=status.HTTP_200_OK, response_model=InvoiceStats)
async def get_invoices_stats(
        uid: UserID,
        invoice_repo: InvoiceReportingDepends
) -> dict[str, Any]:
    return await invoice_repo.invoice_stats(uid=uid)


@router.get("/sum_by_status", status_code=status.HTTP_200_OK, response_model=list[InvoiceByStatus])
async def sum_by_status(
        uid: UserID,
        invoice_repo: InvoiceReportingDepends
) -> list[InvoiceByStatus]:
    return await invoice_repo.get_sum_by_status(uid=uid)


@router.get("/update_overdue", status_code=status.HTTP_200_OK)
async def update_overdue(
        uid: UserID,
        invoice_repo: InvoiceBatchDepends
) -> JSONResponse:

    update_count = await invoice_repo.update_overdue_invoices(uid=uid)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "detail": f"{update_count} overdue invoices"
        }
    )


@router.get("/export_invoices", status_code=status.HTTP_200_OK)
async def export_invoices(
        uid: UserID,
        invoice_repo: InvoiceListingDepends
) -> StreamingResponse:

    result = invoice_repo.a_get_all_invoices(uid=uid)
    return StreamingResponse(get_invoice_json(result), media_type="application/x-ndjson")


@router.get("/invoices_dashboard", status_code=status.HTTP_200_OK)
async def invoice_dashboard(
        uid: UserID,
        invoice_repo: InvoiceReportingDepends
) -> InvoiceStats:

    raw_stats = await invoice_repo.invoice_stats(uid=uid)
    return InvoiceStats(**raw_stats)


#
# @router.get("/bulk_pdf_create", response_model= BulkPDFResponse)
# async def bulk_invoice_to_pdf(
#         invoices_id: Annotated[set[int],
#         Query(min_length=1, max_length=50)],
#         uid: UserID,
#         invoice_repo: InvoiceListingDepends
# ):
#     # TODO (KISS/architecture): endpoint generuje PDF synchronně v request-response
#     # cyklu (asyncio.to_thread + gather), na rozdíl od invoice_to_pdf, který stejnou
#     # práci delegoval na Celery. Zvážit sjednocení na Celery vzor při SRP refaktoringu.
#     # TODO (security, minor): response obsahuje "Denied_id" se seznamem ID, která
#     # nepatří uživateli — potvrzuje existenci cizí faktury. Zvážit odstranění tohoto
#     # pole z response, logging warning stačí.
#     tripped_id = set()
#     coros = []
#     invoice_generator = invoice_repo.get_invoices_by_id(uid, invoices_id)
#     async for invoice in invoice_generator:
#             tripped_id.add(invoice.id)
#             coro = asyncio.to_thread(invoice_pdf, invoice)
#             coros.append(coro)
#
#     pdf_list = await asyncio.gather(*coros, return_exceptions=True)
#
#     invoices_id -= tripped_id
#
#     if invoices_id:
#         logger.warning(f"User {uid} attempted to access invoices not owned: {invoices_id}")
#
#     size = sum([len(pdf) for pdf in pdf_list if not isinstance(pdf, BaseException)])
#     created_count = len(tripped_id) - len([pdf for pdf in pdf_list if isinstance(pdf, BaseException)])
#     return {
#         "status": "ok",
#         "Denied_id": invoices_id,
#         "Created_pdf_count":created_count,
#         "Size": size,
#     }

@router.get("/average_total_amount", status_code=status.HTTP_200_OK, response_model=list[InvoiceResponse])
async def get_invoices_above_average(
        uid: UserID,
        invoice_repo: InvoiceReportingDepends
) -> list[Invoice]:
    return await invoice_repo.get_invoices_above_avg(uid=uid)


@router.get("/{invoice_id}", status_code=status.HTTP_200_OK, response_model=InvoiceResponse)
async def get_one_invoice(
        invoice: GetterInvoice
) -> Invoice:
    return invoice


@router.post("/{invoice_id}/pdf", dependencies=[Depends(invoice_getter)])
async def invoice_to_pdf(
        uid: UserID,
        invoice_id: Annotated[int, Path()]
) -> JSONResponse:
    """ Convert invoice to pdf"""
    #TODO: workflow exrtact to service layer

    pdf_email_workflow = chain(
        generate_pdf.s(invoice_id, uid),
        send_email_task.s(text="Your invoice in pdf is coming")
    )

    pdf_email_workflow.apply_async()

    return JSONResponse(status_code=202,
                        content={
                            "Message": "We work on your task, it will be take a few minutes to complete your task",
                        })


@router.patch("/{invoice_id}/status", status_code=status.HTTP_200_OK, response_model=InvoiceResponse,
              dependencies=[Depends(get_current_user)])
async def change_status(
        invoice: GetterInvoice,
        new_status: Status,
        invoice_repo: InvoiceCRUDDepends
) -> Invoice:
    #TODO: extract validation to service layer
    old_status = invoice.status
    valid_status_change(old_status=old_status, new_status=new_status)
    await invoice_repo.change_invoice_status(invoice=invoice, new_status=new_status)

    return invoice


@router.delete("/{invoice_id}", dependencies=[Depends(get_current_user_active)])
async def delete_draft_invoice(
        invoice: GetterInvoice,
        invoice_repo: InvoiceCRUDDepends
) -> JSONResponse:

    draft_invoice_checker(invoice=invoice)
    result = await invoice_repo.delete_invoice(invoice)
    if result:
        logger.warning(f"Invoice {invoice.id =} {invoice.invoice_number= } was deleted suspicious")
        raise InvoiceConflict(
            "Invoice was already deleted, if it's wasn't you please change a password and contact us to help")

    return JSONResponse(
        status_code=200,
        content={"detail": " Invoice is deleted"}
    )
