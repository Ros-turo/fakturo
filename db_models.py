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

    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    ico = Column(String, nullable=False)
    dic = Column(String, nullable=True)
    city = Column(String, nullable=False)
    psc = Column(String, nullable=False)
    street = Column(String, nullable=False)
    house_number = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    clients = relationship("Client", back_populates="owner")
    invoices = relationship("Invoice", back_populates="owner")
    tokens = relationship("RefreshToken", back_populates="owner", foreign_keys="[RefreshToken.user_id]")


class Client(Base):
    __tablename__ = "clients"

    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    ico = Column(String, nullable=False)
    dic = Column(String, nullable=True)
    city = Column(String, nullable=False)
    psc = Column(String, nullable=False)
    street = Column(String, nullable=True)
    house_number = Column(String, nullable=True)
    vat = Column(Boolean, default=False)
    phone_number = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="clients")
    invoices = relationship("Invoice", back_populates="client")

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

    @is_overdue.expression
    def is_overdue(cls):
        return and_(cls.status != Status.paid, cls.due_date < date.today())

@event.listens_for(Invoice.status, "set")
def on_status_change(target, value, oldvalue, _):
    if str(oldvalue) != "NEVER_SET":
        print(f"{target} change value {oldvalue} -> {value}")
    return None

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    description = Column(String, nullable=False)
    unit_price = Column(Numeric(10,2), nullable=False)
    quantity = Column(Numeric(10,2), nullable=False)
    vat_rate = Column(Integer, nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)

    invoice = relationship("Invoice", back_populates="invoice_items")

class InvoiceTag(Base):
    __tablename__ = "invoice_tags"

    invoice_id = Column(Integer, ForeignKey("invoices.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", back_populates="tags")
    tag = relationship("Tag", back_populates="invoices")

class Tag(Base):
    __tablename__ = "tags"

    __table_args__ = (UniqueConstraint("name","owner_id", name="uq_tag_name_owner"),)

    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invoices = relationship("InvoiceTag", back_populates="tag")

class AuditLog(Base):
    __tablename__ = "audit_log"

    table_name = Column(String, nullable=False)
    row_id = Column(Integer, nullable=False)
    action = Column(SEnum(Action), nullable=False)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    jti = Column(String, nullable=False)
    expired_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_email = Column(String, ForeignKey("users.email"), nullable=False)

    owner = relationship("User", back_populates="tokens", foreign_keys=[user_id])

