"""
 Existuje vlastní exception třída, která nese invoice_id jako atribut (ne jen generický string)
 Existuje registrovaný exception_handler, který tuhle výjimku zpracuje a vrátí 404 s JSON 
 obsahem obsahujícím invoice_id
 Endpoint GET /invoices/{invoice_id} vyhazuje novou výjimku místo přímého HTTPException
 Chování pro klienta zůstává funkčně stejné (404 status, smysluplná zpráva) — jen mechanismus je jiný

Out of scope (pro tenhle issue)

Úprava ostatních endpointů (change_status, invoice_to_pdf) — bude samostatný follow-up issue
Logování při zachycení výjimky — zatím jen vrácení response"""

class InvoiceNotFoundError(Exception):

    def __init__(self, invoice_id: int):
        self.invoice_id = invoice_id
