class FakturoNotFoundError(Exception):

    def __init__(self, resource_name, resource_id):
        self.resource_name: str = resource_name
        self.resource_id: int = resource_id


class InvoiceNotFoundError(FakturoNotFoundError):

    def __init__(self, invoice_id: int):
        super().__init__(resource_name="Invoice", resource_id=invoice_id)

class ClientNotFoundError(FakturoNotFoundError):

    def __init__(self, client_id):
        super().__init__(resource_name="Client", resource_id=client_id)