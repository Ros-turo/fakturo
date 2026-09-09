from datetime import datetime, date, timedelta
from typing import Any
from urllib import response

from fastapi import status
from httpx import AsyncClient
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.invoice_repository import InvoiceRepo
from routers.auth import get_current_user
from routers.invoices import get_invoice_repo
from main import app

def test_get_invoice_repo(db:AsyncSession) -> None:
    repo = get_invoice_repo(db)

    assert isinstance(repo, InvoiceRepo)

@pytest.fixture
async def invoice_json(user_with_one_client:tuple[AsyncClient, int]) -> dict[str, Any]:

    _, client_id = user_with_one_client

    today = date.today()
    tomorrow = today + timedelta(days=1)
    return {"invoice_number": "string",
            "issue_date": f"{today}",
            "due_date": f"{tomorrow}",
            "client_id": client_id,
            "invoice_items": [
                {
                    "description": "string",
                    "unit_price": 100,
                    "quantity": 1,
                    "vat_rate": 21
                }
            ]
        }

@pytest.fixture
async def user_with_one_invoice(user_with_one_client: tuple[AsyncClient, int], invoice_json:dict[str, Any]) -> tuple[AsyncClient, int, int]:
    user, client_id = user_with_one_client
    response = await user.post("/invoices/create_invoice", json=invoice_json)

    response_data = response.json()
    invoice_id = response_data['id']

    return user, client_id, invoice_id


#POST

## create_invoice

async def test_create_invoice_success(user: AsyncClient,
                                      invoice_json: dict[str,Any] ) -> None:
    response = await user.post("/invoices/create_invoice", json=invoice_json)

    response_status_code = response.status_code
    response_data = response.json()
    response_invoice_number = response_data['invoice_number']


    assert response_status_code == status.HTTP_201_CREATED

    assert response_invoice_number == invoice_json['invoice_number']

async def test_create_invoice_with_nonexist_client(user: AsyncClient, invoice_json: dict[str, Any]) -> None:
    invoice_json['client_id'] = 9999999

    response = await user.post("/invoices/create_invoice", json=invoice_json)

    response_data = response.json()
    response_status_code = response.status_code

    assert response_data == {'detail': 'Client 9999999 is not found'}
    assert response_status_code == status.HTTP_404_NOT_FOUND

async def test_create_invoice_validation_error(user: AsyncClient, invoice_json: dict[str, Any]) -> None:

    invoice_json['invoice_number'] = 123

    response = await user.post("/invoices/create_invoice", json=invoice_json)

    response_status_code = response.status_code

    assert response_status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

async def test_create_invoice_empty_body(user: AsyncClient) -> None:

    response = await user.post("/invoices/create_invoice", json={})

    response_status_code = response.status_code

    assert response_status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

## invoice_to_pdf

#GET

## get_one_invoice

async def test_get_one_invoice_success(user_with_one_invoice: tuple[AsyncClient, int, int],
                                       invoice_json: dict[str, Any]) -> None:
    user, client_id, invoice_id = user_with_one_invoice

    response = await user.get(f"/invoices/{invoice_id}")

    response_data = response.json()
    response_status_code = response.status_code

    assert invoice_id == response_data['id']
    assert invoice_json['invoice_number'] == response_data['invoice_number']
    assert response_status_code == status.HTTP_200_OK

async def test_get_one_invoice_not_found_error(user: AsyncClient) -> None:

    response = await user.get(f"/invoices/9999999")
    response_status_code = response.status_code

    assert response_status_code == status.HTTP_404_NOT_FOUND

async def test_get_one_invoice_ownership_isolation(user_with_one_invoice: tuple[AsyncClient, int, int],
                                                   unauthorized_user: AsyncClient,
                                                   user_data: dict[str,str]) -> None:
    user, client_id, invoice_id = user_with_one_invoice

    user_data['email'] = "user_2@example.com"

    auth_response = await unauthorized_user.post("/auth/register", json=user_data)

    new_user = auth_response.json()
    new_user_id = new_user['UID']
    try:
        app.dependency_overrides[get_current_user] = lambda: {"uid": new_user_id}
        get_invoice_response = await unauthorized_user.get(f"/invoices/{invoice_id}")
    finally:
        app.dependency_overrides.pop(get_current_user)
    response_status_code = get_invoice_response.status_code
    response_data = get_invoice_response.json()

    assert response_status_code == status.HTTP_404_NOT_FOUND
    assert response_data == {'detail': f'Invoice {invoice_id} is not found'}




## get_invoices

## get_invoices_stats

## sum_by_sattus

## update_overdue

## export_invoices

## invoices_dashboard

##bulk_invoice_to_pdf

## get_invoices_above_average


# PATCH

## change_status

# DELETE

## delete_draft_invoice