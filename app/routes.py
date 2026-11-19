from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, jsonify, request, session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .models import AuditLog, Candidate, Election, User, Vote

auth_bp = Blueprint("auth", __name__)

STATUSES = {"draft", "scheduled", "open", "closed"}


# ---------- helpers ----------
def now_naive():
    # MySQL election datetimes are stored as local time.
    return datetime.now()

def parse_dt(value):
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def error(message, code=400):
    return jsonify({"error": message}), code


def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return error("Login required", 401)
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user().role != "admin":
            return error("Admin only", 403)
        return fn(*args, **kwargs)
    return wrapper


def log(action, details=None):
    user = current_user()
    db.session.add(AuditLog(actor_user_id=user.id if user else None,
                            action=action, details=details))


def election_is_open(e):
    now = now_naive()
    if e.status != "open":
        return False
    if e.starts_at and now < e.starts_at.replace(tzinfo=None):
        return False
    if e.ends_at and now > e.ends_at.replace(tzinfo=None):
        return False
    return True


def election_json(e):
    return {
        "id": e.id, "title": e.title, "description": e.description,
        "status": e.status,
        "starts_at": e.starts_at.isoformat() if e.starts_at else None,
        "ends_at": e.ends_at.isoformat() if e.ends_at else None,
    }


# ---------- auth ----------
@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or "@" not in email:
        return error("Valid name and email are required")
    if len(password) < 8:
        return error("Password must be at least 8 characters")
    if User.query.filter_by(email=email).first():
        return error("Email already registered", 409)

    user = User(name=name, email=email, role="voter")  # never trust a role from input
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("Email already registered", 409)
    return jsonify({"message": "Registered", "id": user.id}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(data.get("password") or ""):
        return error("Invalid email or password", 401)
    session.clear()
    session["user_id"] = user.id
    return jsonify({"message": "Logged in", "name": user.name, "role": user.role})


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@auth_bp.get("/me")
@login_required
def me():
    u = current_user()
    return jsonify({"id": u.id, "name": u.name, "email": u.email, "role": u.role})


# ---------- elections (admin) ----------
@auth_bp.post("/elections")
@admin_required
def create_election():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return error("Title is required")
    try:
        starts, ends = parse_dt(data.get("starts_at")), parse_dt(data.get("ends_at"))
    except ValueError:
        return error("Dates must be ISO format, e.g. 2026-11-01T09:00:00")
    if starts and ends and ends <= starts:
        return error("End time must be after start time")

    e = Election(title=title, description=data.get("description"),
                 starts_at=starts, ends_at=ends, status="draft")
    db.session.add(e)
    db.session.flush()
    log("election_created", f"election_id={e.id}")
    db.session.commit()
    return jsonify(election_json(e)), 201


@auth_bp.patch("/elections/<int:election_id>/status")
@admin_required
def set_status(election_id):
    e = db.session.get(Election, election_id)
    if not e:
        return error("Election not found", 404)
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in STATUSES:
        return error(f"Status must be one of {sorted(STATUSES)}")
    if status == "open" and e.candidates == []:
        return error("Add candidates before opening")
    e.status = status
    log("election_status_changed", f"election_id={e.id} status={status}")
    db.session.commit()
    return jsonify(election_json(e))


@auth_bp.post("/elections/<int:election_id>/candidates")
@admin_required
def add_candidate(election_id):
    e = db.session.get(Election, election_id)
    if not e:
        return error("Election not found", 404)
    if e.status != "draft":
        return error("Candidates can only be added while the election is a draft")
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return error("Candidate name is required")
    c = Candidate(election_id=e.id, name=name,
                  party_or_group=data.get("party_or_group"),
                  manifesto=data.get("manifesto"))
    db.session.add(c)
    db.session.flush()
    log("candidate_added", f"election_id={e.id} candidate_id={c.id}")
    db.session.commit()
    return jsonify({"id": c.id, "name": c.name}), 201


@auth_bp.delete("/candidates/<int:candidate_id>")
@admin_required
def delete_candidate(candidate_id):
    c = db.session.get(Candidate, candidate_id)
    if not c:
        return error("Candidate not found", 404)
    if c.election.status != "draft" or c.votes:
        return error("Only candidates of draft elections with no votes can be deleted")
    log("candidate_deleted", f"candidate_id={c.id}")
    db.session.delete(c)
    db.session.commit()
    return jsonify({"message": "Deleted"})


# ---------- elections (everyone logged in) ----------
@auth_bp.get("/api/elections")
@login_required
def list_elections():
    q = Election.query
    if current_user().role != "admin":
        q = q.filter(Election.status != "draft")
    return jsonify([election_json(e) for e in q.order_by(Election.id.desc()).all()])


@auth_bp.get("/elections/<int:election_id>/candidates")
@login_required
def list_candidates(election_id):
    e = db.session.get(Election, election_id)
    if not e or (e.status == "draft" and current_user().role != "admin"):
        return error("Election not found", 404)
    return jsonify([{"id": c.id, "name": c.name,
                     "party_or_group": c.party_or_group,
                     "manifesto": c.manifesto} for c in e.candidates])


@auth_bp.post("/api/elections/<int:election_id>/vote")
@login_required
def cast_vote(election_id):
    user = current_user()
    e = db.session.get(Election, election_id)
    if not e:
        return error("Election not found", 404)
    if not election_is_open(e):
        return error("Election is not open for voting", 403)

    candidate_id = (request.get_json(silent=True) or {}).get("candidate_id")
    candidate = Candidate.query.filter_by(id=candidate_id, election_id=e.id).first()
    if not candidate:
        return error("Invalid candidate for this election")

    # Vote and audit entry are saved together or not at all.
    db.session.add(Vote(voter_id=user.id, election_id=e.id, candidate_id=candidate.id))
    log("vote_cast", f"election_id={e.id}")  # candidate not logged, keeps the ballot secret
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("You have already voted in this election", 409)
    return jsonify({"message": "Vote recorded"}), 201


@auth_bp.get("/elections/<int:election_id>/results")
@login_required
def results(election_id):
    e = db.session.get(Election, election_id)
    if not e:
        return error("Election not found", 404)
    if e.status != "closed" and current_user().role != "admin":
        return error("Results are visible after the election closes", 403)

    rows = (
        db.session.query(Candidate.id, Candidate.name, func.count(Vote.id))
        .outerjoin(Vote, Vote.candidate_id == Candidate.id)
        .filter(Candidate.election_id == e.id)
        .group_by(Candidate.id, Candidate.name)
        .all()
    )
    return jsonify({
        "election": election_json(e),
        "results": [{"candidate_id": r[0], "name": r[1], "votes": r[2]} for r in rows],
    })