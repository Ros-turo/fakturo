from datetime import datetime, date
from decimal import Decimal
from typing import List

from sqlalchemy import (Column, Integer, String, Boolean, Numeric, DateTime, ForeignKey, Date,
                        Enum as SEnum, UniqueConstraint, event, select, and_)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from database import Base
from schemas import Status, Action

class User(Base):
    __tablename__ = 'users'

    name:Mapped[str] = mapped_column()
    surname:Mapped[str] = mapped_column()
    ico:Mapped[str] = mapped_column()
    dic:Mapped[str | None] = mapped_column()
    city:Mapped[str] = mapped_column()
    psc:Mapped[str] = mapped_column()
    street:Mapped[str] = mapped_column()
    house_number:Mapped[str] = mapped_column()
    email:Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password:Mapped[str] = mapped_column()
    is_active:Mapped[bool] = mapped_column(default=True)
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    clients:Mapped[List["Client"]] = relationship(back_populates="owner")
    invoices:Mapped[List["Invoice"]] = relationship(back_populates="owner")
    tokens:Mapped[List["RefreshToken"]] = relationship(back_populates="owner", foreign_keys="[RefreshToken.user_id]")


class Client(Base):
    __tablename__ = "clients"

    name:Mapped[str] = mapped_column()
    email:Mapped[str | None] = mapped_column()
    ico:Mapped[str] = mapped_column()
    dic:Mapped[str | None] = mapped_column()
    city:Mapped[str] = mapped_column()
    psc:Mapped[str] = mapped_column()
    street:Mapped[str | None] = mapped_column()
    house_number:Mapped[str | None] = mapped_column()
    vat:Mapped[bool] = mapped_column(default=False)
    phone_number:Mapped[str | None] = mapped_column()
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner_id:Mapped[int] = mapped_column(ForeignKey("users.id"))

    owner:Mapped["User"] = relationship(back_populates="clients")
    invoices:Mapped[List["Invoice"]] = relationship(back_populates="client")

class Invoice(Base):
    __tablename__ = "invoices"

    invoice_number:Mapped[str] = mapped_column(unique=True, index=True)
    issue_date:Mapped[date] = mapped_column(server_default=func.current_date())
    due_date:Mapped[date] = mapped_column()
    status:Mapped[Status] = mapped_column(SEnum(Status), default=Status.draft)
    created_at:Mapped[datetime] = mapped_column(server_default=func.now())
    total_amount:Mapped[Decimal] = mapped_column()

    owner_id:Mapped[int] = mapped_column(ForeignKey("users.id"))
    client_id:Mapped[int] = mapped_column(ForeignKey("clients.id"))

    owner:Mapped["User"] = relationship(back_populates="invoices")
    client:Mapped["Client"] = relationship(back_populates="invoices")
    invoice_items:Mapped[List["InvoiceItem"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    tags:Mapped[List["InvoiceTag"]] = relationship(back_populates="invoice")

    @hybrid_property
    def is_overdue(self):
        return self.status != Status.paid and self.due_date < date.today()

    @is_overdue.expression # type: ignore[no-redef]
    def is_overdue(cls):
        return and_(cls.status != Status.paid, cls.due_date < date.today())

@event.listens_for(Invoice.status, "set")
def on_status_change(target, value, oldvalue, _):
    if str(oldvalue) != "NEVER_SET":
        print(f"{target} change value {oldvalue} -> {value}")
    return None

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    description:Mapped[str] = mapped_column()
    unit_price:Mapped[Decimal] = mapped_column(Numeric(10,2))
    quantity:Mapped[Decimal] = mapped_column(Numeric(10,2))
    vat_rate:Mapped[int] = mapped_column()
    invoice_id:Mapped[int] = mapped_column(ForeignKey("invoices.id"))

    invoice:Mapped["Invoice"] = relationship(back_populates="invoice_items")

class InvoiceTag(Base):
    __tablename__ = "invoice_tags"

    invoice_id:Mapped[int] = mapped_column(ForeignKey("invoices.id"), primary_key=True)
    tag_id:Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True)
    added_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    invoice:Mapped["Invoice"] = relationship(back_populates="tags")
    tag:Mapped["Tag"] = relationship(back_populates="invoices")

class Tag(Base):
    __tablename__ = "tags"

    __table_args__ = (UniqueConstraint("name","owner_id", name="uq_tag_name_owner"),)

    name:Mapped[str] = mapped_column()
    owner_id:Mapped[int] = mapped_column(ForeignKey("users.id"))

    invoices:Mapped[List["InvoiceTag"]] = relationship(back_populates="tag")

class AuditLog(Base):
    __tablename__ = "audit_log"

    table_name:Mapped[str] = mapped_column()
    row_id:Mapped[int] = mapped_column()
    action:Mapped[Action] = mapped_column(SEnum(Action))
    old_value:Mapped[str | None] = mapped_column()
    new_value:Mapped[str | None] = mapped_column()
    changed_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    jti:Mapped[str] = mapped_column()
    expired_at:Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked:Mapped[bool] = mapped_column(default=False)
    user_id:Mapped[int] = mapped_column(ForeignKey("users.id"))
    user_email:Mapped[str] = mapped_column(ForeignKey("users.email"))

    owner:Mapped["User"] = relationship(back_populates="tokens", foreign_keys=[user_id])

