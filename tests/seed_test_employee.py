"""
Seeds a single test employee (id=1) so eval suites have a valid FK target
for ConversationSession.employee_id. Used only in CI/local test setup -
never run this against a real production database.
Run: python -m tests.seed_test_employee
"""
from app.database import SessionLocal
from app.models.employee import Employee
from app.core.security import hash_password

db = SessionLocal()
existing = db.query(Employee).filter(Employee.id == 1).first()
if not existing:
    employee = Employee(
        full_name="CI Test Employee",
        email="ci-test@anchor.dev",
        hashed_password=hash_password("CITestPassword123!"),
        role="employee",
    )
    db.add(employee)
    db.commit()
    print("Seeded test employee id=1")
else:
    print("Test employee id=1 already exists")
db.close()
