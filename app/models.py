from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String(255), unique=True, index=True)
    registration_date = Column(Date)
    credits = relationship("Credit", back_populates="user")


class Credit(Base):
    __tablename__ = "credits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    issuance_date = Column(Date)
    return_date = Column(Date)
    actual_return_date = Column(Date, nullable=True)
    body = Column(Float)
    percent = Column(Float)

    user = relationship("User", back_populates="credits")
    payments = relationship("Payment", back_populates="credit")


class Dictionary(Base):
    __tablename__ = "dictionary"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    period = Column(Date)
    sum = Column(Float)
    category_id = Column(Integer, ForeignKey("dictionary.id"))


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    sum = Column(Float)
    payment_date = Column(Date)
    credit_id = Column(Integer, ForeignKey("credits.id"))
    type_id = Column(Integer, ForeignKey("dictionary.id"))

    credit = relationship("Credit", back_populates="payments")
