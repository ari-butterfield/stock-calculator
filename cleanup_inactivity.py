from datetime import datetime, timedelta
from extensions import db
from models import Visitor, Task


def cleanup_stale_visitors(days=14):
    """Delete visitors and their tasks whose last_seen is older than `days` days.

    This can be scheduled to run daily.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    stale = Visitor.query.filter(Visitor.last_seen < cutoff).all()
    if not stale:
        return 0
    uuids = [v.uuid for v in stale]
    try:
        # delete tasks for these visitors
        Task.query.filter(Task.visitor_uuid.in_(uuids)).delete(synchronize_session=False)
        # delete visitor rows
        Visitor.query.filter(Visitor.uuid.in_(uuids)).delete(synchronize_session=False)
        db.session.commit()
        return len(uuids)
    except Exception:
        db.session.rollback()
        raise
