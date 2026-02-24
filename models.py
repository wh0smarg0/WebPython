from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base


class Taxpayer(Base):
    __tablename__ = "taxpayers"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    tin = Column(String, unique=True)
    records = relationship("TaxRecord", back_populates="taxpayer", cascade="all, delete-orphan")


class TaxType(Base):
    __tablename__ = "tax_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    rate = Column(Float)
    records = relationship("TaxRecord", back_populates="tax_type")


class TaxRecord(Base):
    __tablename__ = "tax_records"
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    taxpayer_id = Column(Integer, ForeignKey("taxpayers.id"))
    tax_type_id = Column(Integer, ForeignKey("tax_types.id"))

    taxpayer = relationship("Taxpayer", back_populates="records")
    tax_type = relationship("TaxType", back_populates="records")
