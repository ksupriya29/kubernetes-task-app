"""
SQLAlchemy models.
"""
from datetime import datetime, timezone

from .database import db


class Task(db.Model):
    """Represents a single task."""

    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True, default="")
    completed = db.Column(db.Boolean, nullable=False, default=False)
    priority = db.Column(
        db.String(10),
        nullable=False,
        default="medium",
    )  # low | medium | high
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        """Serialise the model to a plain Python dict."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description or "",
            "completed": self.completed,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        status = "✓" if self.completed else "○"
        return f"<Task {self.id} [{status}] {self.title!r}>"
