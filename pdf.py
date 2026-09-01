from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML # type: ignore [import-untyped]
from db_models import Invoice


def invoice_pdf(invoice: Invoice):
    env = Environment(loader=FileSystemLoader('templates'), autoescape=select_autoescape("html"))
    report = env.get_template("invoice.html")
    html = HTML(string=report.render(invoice=invoice))
    return html.write_pdf()

def bulk_pdf_converter(invoices_id:set[int]):
    ...