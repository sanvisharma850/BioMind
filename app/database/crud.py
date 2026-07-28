from sqlalchemy.orm import Session

from app.database.models import Report


def create_report(
    db: Session,
    disease: str,
    result_json: str,
):
    report = Report(
        disease=disease,
        result_json=result_json,
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return report


def get_reports(db: Session):
    return (
        db.query(Report)
        .order_by(Report.created_at.desc())
        .all()
    )