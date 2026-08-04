from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.employee import Employee
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(Employee).filter(Employee.email == request.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    employee = Employee(
        full_name=request.full_name,
        email=request.email,
        hashed_password=hash_password(request.password),
        role="employee",
        generation=request.generation,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)

    token = create_access_token(employee.id, employee.role)
    return TokenResponse(
        access_token=token,
        employee_id=employee.id,
        full_name=employee.full_name,
        role=employee.role,
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.email == request.email).first()

    # Deliberately identical error for "no such user" and "wrong password" -
    # distinguishing them lets an attacker enumerate valid email addresses.
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
    )

    if not employee:
        raise invalid_credentials
    if not verify_password(request.password, employee.hashed_password):
        raise invalid_credentials

    token = create_access_token(employee.id, employee.role)
    return TokenResponse(
        access_token=token,
        employee_id=employee.id,
        full_name=employee.full_name,
        role=employee.role,
    )
