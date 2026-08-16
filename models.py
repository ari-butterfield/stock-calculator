from extensions import db
from datetime import datetime


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_uuid = db.Column(db.String(36), nullable=False, index=True)
    ticker = db.Column(db.String(20), nullable=False)
    company_name = db.Column(db.String(120), nullable=True)
    pe = db.Column(db.Float, nullable=True)
    peg = db.Column(db.Float, nullable=True)
    roe = db.Column(db.Float, nullable=True)
    weekly_return = db.Column(db.Float, nullable=True)
    weekly_return_std = db.Column(db.Float, nullable=True)
    sharpe_ratio = db.Column(db.Float, nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Task(visitor={self.visitor_uuid}, ticker={self.ticker}, company={self.company_name}, pe={self.pe}, peg={self.peg}, roe={self.roe}, weekly_return={self.weekly_return}, weekly_return_std={self.weekly_return_std}, sharpe_ratio={self.sharpe_ratio})"


class Visitor(db.Model):
    """Tracks per-browser visitor UUID and last seen timestamp for cleanup."""
    uuid = db.Column(db.String(36), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"Visitor(uuid={self.uuid}, last_seen={self.last_seen})"
