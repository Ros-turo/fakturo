from httpx import AsyncClient
import pytest

@pytest.mark.parametrize(
    argnames= "router, path",
    argvalues=[("/invoices", "/"), ("/invoices", "/stats"),("/invoices", "/1"),
               ("/clients", "/"), ("/clients", "/1"), ("/clients", "/ares/12345678"),
               ("/auth", "/sessions")],
    ids=["All_invoices", "stats", "Invoice_with_id_1",
         "All_clients", "Client_with_id_1", "Ares",
         "Auth_sessions"],
)
async def test_endpoints_security_get(unauthorized_user:AsyncClient, router:str, path: str):
    response = await unauthorized_user.get(f"{router}{path}")


    assert response.status_code == 401

@pytest.mark.parametrize(
    argnames= "router, path",
    argvalues=[("/invoices", "/create_invoice"), ("/clients", "/"), ("/auth", "/logout_device/1231")],
    ids=["Create_invoice", "Create_client", "logout_by_jwt",]
)
async def test_endpoints_security_post(unauthorized_user:AsyncClient, router:str, path: str):
    response = await unauthorized_user.post(url=f"{router}{path}", json="test")

    assert response.status_code == 401

@pytest.mark.parametrize(
    argnames= "router, path",
    argvalues=[("/invoices", "/1"), ("/clients", "/1")],
    ids=["Invoice_with_id_1", "Client_with_id_1"]
)
async def test_endpoints_security_delete(unauthorized_user:AsyncClient, router:str, path: str):
    response = await unauthorized_user.delete(url=f"{router}{path}")

    assert response.status_code == 401