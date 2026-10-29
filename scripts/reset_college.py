"""Reset script for E2E tests."""
import sys
import argparse

sys.path.insert(0, "backend")
from app.db import SessionLocal, get_redis
from app.models import (
    ActivationRequest, Institution, User, Student,
    ValidationFlag, Justification, SeatDeclaration,
    Submission, ReviewItem, Notification, VerifiedRecord,
    ConsentRequest, Course
)

def reset_institution(aicte_id: str, student_apaar_id: str | None = None):
    db = SessionLocal()
    r = next(get_redis())
    keys = r.keys("ratelimit:*")
    if keys:
        r.delete(*keys)

    inst = db.query(Institution).filter_by(aicte_id=aicte_id).first()
    if inst:
        c_ids = [c.id for c in inst.courses]
        st_ids = [s.id for s in db.query(Student.id).filter_by(institution_id=inst.id).all()]
        if st_ids:
            db.query(VerifiedRecord).filter(VerifiedRecord.student_id.in_(st_ids)).delete(synchronize_session=False)
            db.query(ValidationFlag).filter(ValidationFlag.student_id.in_(st_ids)).delete(synchronize_session=False)
            db.query(Student).filter_by(institution_id=inst.id).delete(synchronize_session=False)

        if c_ids:
            db.query(SeatDeclaration).filter(SeatDeclaration.course_id.in_(c_ids)).delete(synchronize_session=False)
            db.query(ValidationFlag).filter(ValidationFlag.course_id.in_(c_ids)).delete(synchronize_session=False)

        sub_ids = [s.id for s in db.query(Submission.id).filter_by(institution_id=inst.id).all()]
        if sub_ids:
            db.query(ReviewItem).filter(ReviewItem.submission_id.in_(sub_ids)).delete(synchronize_session=False)
            db.query(Submission).filter_by(institution_id=inst.id).delete(synchronize_session=False)

        db.query(Notification).filter_by(institution_id=inst.id).delete(synchronize_session=False)
        db.query(ActivationRequest).filter_by(institution_id=inst.id).delete(synchronize_session=False)
        db.query(User).filter_by(institution_id=inst.id).delete(synchronize_session=False)
        inst.account_status = "not_activated"
        db.commit()

    if student_apaar_id:
        db.query(ConsentRequest).filter_by(apaar_id=student_apaar_id).delete(synchronize_session=False)
        db.commit()

    db.close()
    print(f"Reset completed for {aicte_id}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--aicte-id", required=True)
    parser.add_argument("--apaar-id", required=False, default=None)
    args = parser.parse_args()
    reset_institution(args.aicte_id, args.apaar_id)
