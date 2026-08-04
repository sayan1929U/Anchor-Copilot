from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import decode_access_token
from app.models.employee import Employee

bearer_scheme = HTTPBearer()


def get_current_employee(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Employee:
    """
    Extracts and validates the JWT from the Authorization header, then loads
    the real Employee record. Every protected endpoint depends on this instead
    of trusting an employee_id passed in the request body - the whole point
    is that the caller can no longer claim to be anyone they want.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    employee_id = payload.get("sub")
    if employee_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    employee = db.query(Employee).filter(Employee.id == int(employee_id)).first()
    if employee is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Employee not found")

    return employee


def require_manager(employee: Employee = Depends(get_current_employee)) -> Employee:
    """Additional check for manager-only endpoints, e.g. the audit dashboard."""
    if employee.role != "manager":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager access required")
    return employee
