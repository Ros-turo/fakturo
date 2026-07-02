from typing import Annotated
from datetime import date, datetime
from enum import Enum

from decimal import Decimal
from pydantic import BaseModel, Field, EmailStr, ConfigDict, model_validator, field_validator, computed_field


class Status(str, Enum):
    draft = "draft"
    sent = "sent"
    paid = "paid"
    overdue = "overdue"

class Action(str, Enum):
    update = "UPDATE"
    insert = "INSERT"
    delete = "DELETE"

class OrderBy(str, Enum):
    created_at = "created_at"
    issue_date = "issue_date"
    due_date = "due_date"

class OrderDir(str, Enum):
    ascended = "asc"
    descended = "desc"

class VatRate(int, Enum):
    basic = 21
    reduce = 12


class ClientDefault(BaseModel):
    name: str
    ico: Annotated[str, Field(pattern=r"\d{8}")]
    dic: Annotated[str | None, Field(pattern=r"(CZ|SK)(\d{8}|\d{10})")] = None
    city: str
    psc: str
    street: str | None = None
    house_number: str | None = None
    vat: bool = False

    model_config = ConfigDict(coerce_numbers_to_str=True, from_attributes=True)

class ClientAres(ClientDefault):
    pass

class ClientCreate(ClientDefault):

    email: EmailStr | None = None
    phone_number: Annotated[str | None, Field(pattern=r"\d{9}")] = None

class ClientResponse(ClientCreate):

    id: int

class InvoiceItemCreate(BaseModel):

    description: str
    unit_price: Decimal
    quantity: Decimal
    vat_rate: VatRate


    @computed_field
    @property
    def subtotal(self) -> Decimal:
        return round(self.unit_price*self.quantity, 2)

    @computed_field
    @property
    def total_with_vat(self) -> Decimal:
        return round((self.subtotal*(1+Decimal(self.vat_rate/100))), 2)


class InvoiceItemResponse(InvoiceItemCreate):
    id: int
    invoice_id: int

    model_config = ConfigDict(from_attributes=True)

class InvoiceCreate(BaseModel):

    invoice_number: str
    issue_date: Annotated[date, Field(default_factory=date.today)]
    due_date: Annotated[date, Field()]
    invoice_items: list[InvoiceItemCreate]
    client_id: Annotated[int, Field(ge=1)]

    # @field_validator("due_date")
    # @classmethod
    # def due_date_not_in_past(cls, value: date) -> date:
    #     if value < date.today():
    #         raise ValueError("Due date cannot be in the past" )
    #     return value

    @model_validator(mode="after")
    def due_date_after_issue_date(self):
        if self.due_date < self.issue_date:
            raise ValueError("Due date cannot be early than issue date")
        return self


class InvoiceResponse(InvoiceCreate):
    id: int
    status: Status
    created_at: datetime
    invoice_items: list[InvoiceItemResponse]
    total_amount: Decimal
    owner_id: int

    model_config = ConfigDict(from_attributes=True)

class InvoiceListResponse(BaseModel):
    total: int
    items: list[InvoiceResponse]

    model_config = ConfigDict(from_attributes=True)

class InvoiceByStatus(BaseModel):
    status: Status
    count: int
    total: Decimal

    model_config = ConfigDict(from_attributes=True)

class InvoiceStats(BaseModel):
    total_invoices: int
    total_revenue: Decimal
    by_status: list[InvoiceByStatus]
    overdue_updated: int | None

    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):

    name: Annotated[str, Field(min_length=5)]
    password: Annotated[str, Field(min_length=8)]
    email: EmailStr
    name: str
    surname: str
    ico: Annotated[str, Field(pattern=r"\d{8}")]
    dic: Annotated[str | None, Field(pattern=r"(CZ|SK)(\d{8}|\d{10})")] = None
    city: str
    psc: str
    street: str | None = None
    house_number: str | None = None

class BulkPDFResponse(BaseModel):

    status: str
    denied_ids: set[int]
    created_count: int
    size: int