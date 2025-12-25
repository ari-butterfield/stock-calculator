from app import db
from datetime import datetime


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_uuid = db.Column(db.String(36), nullable=False, index=True)
    ticker = db.Column(db.String(20), nullable=False)
    pe_ratio = db.Column(db.Float, nullable=True)
    peg = db.Column(db.Float, nullable=True)
    roe = db.Column(db.Float, nullable=True)
    risk = db.Column(db.Float, nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Task(visitor={self.visitor_uuid}, ticker={self.ticker}, pe={self.pe_ratio}, peg={self.peg}, roe={self.roe}, risk={self.risk})"
