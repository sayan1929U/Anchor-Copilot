from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from app.database import Base

class ManagerNudge(Base):
    __tablename__ = "manager_nudges"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("conversation_sessions.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    nudge_type = Column(String, nullable=False)     # "recognition" | "learning_support" | "career_check_in"
    message = Column(Text, nullable=False)            # the actual nudge text for the manager
    status = Column(String, default="pending")        # "pending" | "acknowledged" | "dismissed"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
