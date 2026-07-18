"""Students: search/list, create (librarian only), and per-student history."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_librarian
from ..models import Book, BorrowRecord, Student
from ..schemas import BorrowRecordOut, StudentCreate, StudentOut

router = APIRouter(prefix="/students", tags=["students"])


def _active_book_ids(db: Session, student_pk: int) -> list[str]:
    """book_id strings the student currently holds (return_date IS NULL)."""
    rows = (
        db.query(Book.book_id)
        .join(BorrowRecord, BorrowRecord.book_pk == Book.id)
        .filter(
            BorrowRecord.student_pk == student_pk,
            BorrowRecord.return_date.is_(None),
        )
        .all()
    )
    return [r[0] for r in rows]


@router.get("", response_model=list[StudentOut])
def list_students(
    q: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    query = db.query(Student)
    if q:
        query = query.filter(Student.name.ilike(f"%{q}%"))
    students = query.order_by(Student.student_id).all()
    return [
        StudentOut(
            student_id=s.student_id,
            name=s.name,
            borrowed_book_ids=_active_book_ids(db, s.id),
        )
        for s in students
    ]


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def add_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    _=Depends(require_librarian),
):
    if db.query(Student).filter(Student.student_id == payload.student_id).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "student_id already exists")
    student = Student(student_id=payload.student_id, name=payload.name)
    db.add(student)
    db.commit()
    db.refresh(student)
    return StudentOut(student_id=student.student_id, name=student.name, borrowed_book_ids=[])


@router.get("/{student_id}/borrowed", response_model=list[BorrowRecordOut])
def borrow_history(
    student_id: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")
    records = (
        db.query(BorrowRecord)
        .filter(BorrowRecord.student_pk == student.id)
        .order_by(BorrowRecord.issue_date.desc())
        .all()
    )
    return [
        BorrowRecordOut(
            id=r.id,
            book_id=r.book.book_id,
            title=r.book.title,
            student_id=student.student_id,
            student_name=student.name,
            issue_date=r.issue_date,
            due_date=r.due_date,
            return_date=r.return_date,
            penalty=r.penalty,
        )
        for r in records
    ]
