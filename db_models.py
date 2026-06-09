from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, ForeignKey, Date, Enum as SEnum, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from schemas import Status

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer,primary_key=True, index=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    ico = Column(String, nullable=False)
    dic = Column(String, nullable=True)
    city = Column(String, nullable=False)
    psc = Column(String, nullable=False)
    street = Column(String, nullable=True)
    house_number = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    clients = relationship("Client", back_populates="owner")
    invoices = relationship("Invoice", back_populates="owner")


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
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

    id = Column(Integer, primary_key=True)
    invoice_number = Column(String, unique=True, index=True, nullable=False)
    issue_date = Column(Date, server_default=func.current_date(), nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(SEnum(Status), nullable=False, default=Status.draft)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    total_amount = Column(Numeric(10,2), nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    owner = relationship("User", back_populates="invoices")
    client = relationship("Client", back_populates="invoices")
    invoice_items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    tags = relationship("InvoiceTag", back_populates="invoice")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True)
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

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invoices = relationship("InvoiceTag", back_populates="tag")

