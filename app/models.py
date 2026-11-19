from datetime import datetime, timezone

from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("voter", "admin", name="user_roles"),
                     nullable=False, default="voter")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    votes = db.relationship("Vote", back_populates="voter")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Election(db.Model):
    __tablename__ = "elections"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    starts_at = db.Column(db.DateTime(timezone=True))
    ends_at = db.Column(db.DateTime(timezone=True))
    status = db.Column(
        db.Enum("draft", "scheduled", "open", "closed", name="election_statuses"),
        nullable=False,
        default="draft",
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    candidates = db.relationship(
        "Candidate", back_populates="election", cascade="all, delete-orphan"
    )
    votes = db.relationship("Vote", back_populates="election")


class Candidate(db.Model):
    __tablename__ = "candidates"

    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(
        db.Integer, db.ForeignKey("elections.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(160), nullable=False)
    party_or_group = db.Column(db.String(160))
    manifesto = db.Column(db.Text)

    election = db.relationship("Election", back_populates="candidates")
    votes = db.relationship("Vote", back_populates="candidate")


class Vote(db.Model):
    __tablename__ = "votes"
    __table_args__ = (
        db.UniqueConstraint("voter_id", "election_id", name="uq_vote_voter_election"),
    )

    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    election_id = db.Column(
        db.Integer, db.ForeignKey("elections.id", ondelete="CASCADE"), nullable=False
    )
    candidate_id = db.Column(
        db.Integer, db.ForeignKey("candidates.id"), nullable=False
    )
    cast_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    voter = db.relationship("User", back_populates="votes")
    election = db.relationship("Election", back_populates="votes")
    candidate = db.relationship("Candidate", back_populates="votes")


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    actor = db.relationship("User")
