from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="employee")
    generation = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
