from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from .extensions import db
from .models import User, Election, Candidate, Vote
from .routes import current_user
from sqlalchemy import func


# --------------------------------------------------
# BLUEPRINT
# --------------------------------------------------
web_bp = Blueprint("web", __name__)


# --------------------------------------------------
# AUTOMATIC ELECTION STATUS UPDATE
# --------------------------------------------------
def update_election_statuses():
    now = datetime.now()

    elections = Election.query.filter(
        Election.status.in_(["scheduled", "open"])
    ).all()

    for election in elections:

        # Close election after end time
        if election.ends_at and now >= election.ends_at:
            election.status = "closed"

        # Open election when start time is reached
        elif election.starts_at and now >= election.starts_at:
            election.status = "open"

    db.session.commit()


# --------------------------------------------------
# LOGIN PAGE
# --------------------------------------------------
@web_bp.get("/login")
def login_page():
    return render_template("auth/login.html")


# --------------------------------------------------
# REGISTER PAGE
# --------------------------------------------------
@web_bp.get("/register")
def register_page():
    return render_template("auth/register.html")


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------
@web_bp.get("/dashboard")
def dashboard():
    user = current_user()

    if not user:
        return redirect(url_for("web.login_page"))

    update_election_statuses()

    available_elections = (
        Election.query
        .filter(Election.status == "open")
        .order_by(Election.id.desc())
        .all()
    )

    voting_history = (
        Vote.query
        .filter_by(voter_id=user.id)
        .order_by(Vote.cast_at.desc())
        .all()
    )

    votes_cast = len(voting_history)

    return render_template(
        "voter/dashboard.html",
        user=user,
        available_elections=available_elections,
        votes_cast=votes_cast,
        voting_history=voting_history,
    )


# --------------------------------------------------
# ADMIN DASHBOARD
# --------------------------------------------------
@web_bp.get("/admin/dashboard")
def admin_dashboard():
    user = current_user()

    if not user:
        return redirect(url_for("web.login_page"))

    if user.role != "admin":
        flash(
            "You are not authorized to access the admin dashboard.",
            "danger",
        )
        return redirect(url_for("web.dashboard"))

    update_election_statuses()

    total_elections = Election.query.count()
    total_voters = User.query.filter_by(role="voter").count()
    total_candidates = Candidate.query.count()
    total_votes = Vote.query.count()

    return render_template(
        "admin/dashboard.html",
        user=user,
        total_elections=total_elections,
        total_voters=total_voters,
        total_candidates=total_candidates,
        total_votes=total_votes,
    )


# --------------------------------------------------
# ADMIN ELECTIONS
# --------------------------------------------------
@web_bp.route("/admin/elections", methods=["GET", "POST"])
def admin_elections():
    user = current_user()

    if not user:
        return redirect(url_for("web.login_page"))

    if user.role != "admin":
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for("web.dashboard"))

    update_election_statuses()

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        starts_at_raw = request.form.get("starts_at", "").strip()
        ends_at_raw = request.form.get("ends_at", "").strip()

        if not title:
            flash("Election title is required.", "danger")
            return redirect(url_for("web.admin_elections"))

        if not starts_at_raw or not ends_at_raw:
            flash("Both start and end dates are required.", "danger")
            return redirect(url_for("web.admin_elections"))

        try:
            starts_at = datetime.fromisoformat(starts_at_raw)
            ends_at = datetime.fromisoformat(ends_at_raw)

        except ValueError:
            flash("Please enter valid election dates.", "danger")
            return redirect(url_for("web.admin_elections"))

        if starts_at >= ends_at:
            flash("End time must be after start time.", "danger")
            return redirect(url_for("web.admin_elections"))

        election = Election(
            title=title,
            description=description,
            starts_at=starts_at,
            ends_at=ends_at,
            status="scheduled",
        )

        db.session.add(election)
        db.session.commit()

        flash("Election scheduled successfully!", "success")
        return redirect(url_for("web.admin_elections"))

    elections = Election.query.order_by(Election.id.desc()).all()

    return render_template(
        "admin/elections.html",
        user=user,
        elections=elections,
    )
# --------------------------------------------------
# ADMIN CANDIDATE MANAGEMENT
# --------------------------------------------------

@web_bp.route("/admin/candidates", methods=["GET", "POST"])
def admin_candidates():
    user = current_user()

    if not user:
        return redirect(url_for("web.login_page"))

    if user.role != "admin":
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for("web.dashboard"))

    if request.method == "POST":
        election_id = request.form.get("election_id")
        name = request.form.get("name", "").strip()
        party_or_group = request.form.get("party_or_group", "").strip()
        manifesto = request.form.get("manifesto", "").strip()

        if not election_id or not name:
            flash("Please select an election and enter a candidate name.", "danger")
            return redirect(url_for("web.admin_candidates"))

        election = Election.query.get(election_id)

        if not election:
            flash("Selected election does not exist.", "danger")
            return redirect(url_for("web.admin_candidates"))

        if election.status == "closed":
            flash("Candidates cannot be added to a closed election.", "danger")
            return redirect(url_for("web.admin_candidates"))

        if Vote.query.filter_by(election_id=election.id).first():
            flash("Candidates cannot be changed after voting has started.", "danger")
            return redirect(url_for("web.admin_candidates"))

        candidate = Candidate(
            election_id=election.id,
            name=name,
            party_or_group=party_or_group,
            manifesto=manifesto,
        )

        db.session.add(candidate)
        db.session.commit()

        flash("Candidate added successfully!", "success")
        return redirect(url_for("web.admin_candidates"))

    elections = Election.query.order_by(Election.id.desc()).all()

    candidates = (
    Candidate.query
    .join(Election)
    .filter(Election.status != "closed")
    .order_by(Candidate.id.desc())
    .all()
)

    return render_template(
        "admin/candidates.html",
        user=user,
        elections=elections,
        candidates=candidates,
    )


# DELETE CANDIDATE

@web_bp.route(
    "/admin/candidates/<int:candidate_id>/delete",
    methods=["POST"],
)
def delete_candidate(candidate_id):

    user = current_user()

    if not user:
        return redirect(url_for("web.login_page"))

    if user.role != "admin":
        flash("You are not authorized to perform this action.", "danger")
        return redirect(url_for("web.dashboard"))

    candidate = Candidate.query.get_or_404(candidate_id)

    # Prevent deletion from ongoing or completed elections
    if candidate.election.status in ["open", "closed"]:
        flash(
            "Candidates cannot be deleted from ongoing or completed elections.",
            "warning"
        )
        return redirect(url_for("web.admin_candidates"))

    # Prevent deletion if the candidate has recorded votes
    existing_vote = Vote.query.filter_by(
        candidate_id=candidate.id
    ).first()

    if existing_vote:
        flash(
            "This candidate has recorded votes and cannot be deleted.",
            "danger"
        )
        return redirect(url_for("web.admin_candidates"))

    # Delete candidate
    db.session.delete(candidate)
    db.session.commit()

    flash("Candidate deleted successfully!", "success")

    return redirect(url_for("web.admin_candidates"))

# --------------------------------------------------
# ELECTION DETAILS PAGE
# --------------------------------------------------
@web_bp.get("/elections/<int:election_id>")
def election_details(election_id):
    user = current_user()

    if not user:
        return redirect(url_for("web.login_page"))

    update_election_statuses()

    election = Election.query.get_or_404(election_id)

    candidates = Candidate.query.filter_by(
        election_id=election.id
    ).all()

    already_voted = Vote.query.filter_by(
        voter_id=user.id,
        election_id=election.id,
    ).first() is not None

    return render_template(
        "voter/election_details.html",
        election=election,
        candidates=candidates,
        already_voted=already_voted,
        user=user,
    )


# --------------------------------------------------
# ELECTIONS HTML PAGE
# --------------------------------------------------
@web_bp.get("/elections")
def elections_page():
    user = current_user()

    if not user:
        return redirect(url_for("web.login_page"))

    update_election_statuses()

    elections = (
        Election.query
        .filter(Election.status != "draft")
        .order_by(Election.id.desc())
        .all()
    )

    print(
        "DEBUG ELECTIONS:",
        [(e.id, e.title, e.status) for e in elections]
    )

    voting_history = Vote.query.filter_by(
        voter_id=user.id
    ).all()

    voted_election_ids = {
        vote.election_id for vote in voting_history
    }

    return render_template(
        "voter/elections.html",
        user=user,
        elections=elections,
        voted_election_ids=voted_election_ids,
        now=datetime.now(),
    )


# --------------------------------------------------
# RESULTS HTML PAGE
# --------------------------------------------------
@web_bp.get("/results")
def results_page():
    user = current_user()

    if not user:
        return redirect(url_for("web.login_page"))

    update_election_statuses()

    elections = (
        Election.query
        .filter(Election.status == "closed")
        .order_by(Election.id.desc())
        .all()
    )

    results_by_election = {}

    for election in elections:

        rows = (
            db.session.query(
                Candidate.id,
                Candidate.name,
                Candidate.party_or_group,
                func.count(Vote.id).label("vote_count"),
            )
            .outerjoin(
                Vote,
                Vote.candidate_id == Candidate.id,
            )
            .filter(
                Candidate.election_id == election.id,
            )
            .group_by(
                Candidate.id,
                Candidate.name,
                Candidate.party_or_group,
            )
            .order_by(
                func.count(Vote.id).desc(),
            )
            .all()
        )

        results_by_election[election.id] = rows

    return render_template(
        "voter/results.html",
        user=user,
        elections=elections,
        results_by_election=results_by_election,
    )


# --------------------------------------------------
# VOTE PAGE
# --------------------------------------------------
@web_bp.route(
    "/elections/<int:election_id>/vote",
    methods=["GET", "POST"],
)
def submit_vote(election_id):
    user = current_user()

    if not user:
        return redirect(url_for("web.login_page"))

    # Prevent admin accounts from voting
    if (user.role or "").strip().lower() == "admin":
        flash("Admin accounts are not allowed to vote.", "warning")

        return render_template(
            "errors/403.html",
            user=user,
        ), 403

    update_election_statuses()

    election = Election.query.get_or_404(election_id)

    # Allow voting only when election is open
    if election.status != "open":
        flash(
            "Voting is not currently open for this election.",
            "warning",
        )
        return redirect(url_for("web.elections_page"))

    # Prevent duplicate voting
    already_voted = Vote.query.filter_by(
        voter_id=user.id,
        election_id=election.id,
    ).first()

    if already_voted:
        flash(
            "You have already voted in this election.",
            "warning",
        )

        return redirect(
            url_for(
                "web.confirmation",
                election_id=election.id,
            )
        )

    if request.method == "POST":

        candidate_id = request.form.get("candidate_id")

        if not candidate_id:
            flash(
                "Please select a candidate.",
                "danger",
            )

            return redirect(
                url_for(
                    "web.submit_vote",
                    election_id=election.id,
                )
            )

        candidate = Candidate.query.filter_by(
            id=candidate_id,
            election_id=election.id,
        ).first()

        if not candidate:
            flash(
                "Invalid candidate selected.",
                "danger",
            )

            return redirect(
                url_for(
                    "web.submit_vote",
                    election_id=election.id,
                )
            )

        vote = Vote(
            voter_id=user.id,
            election_id=election.id,
            candidate_id=candidate.id,
        )

        db.session.add(vote)

        try:
            db.session.commit()

        except Exception:
            db.session.rollback()

            flash(
                "Unable to record your vote. Please try again.",
                "danger",
            )

            return redirect(
                url_for(
                    "web.submit_vote",
                    election_id=election.id,
                )
            )

        flash(
            "Your vote has been submitted successfully!",
            "success",
        )

        return redirect(
            url_for(
                "web.confirmation",
                election_id=election.id,
            )
        )

    candidates = Candidate.query.filter_by(
        election_id=election.id
    ).all()

    return render_template(
        "voter/vote.html",
        election=election,
        candidates=candidates,
        user=user,
    )


# --------------------------------------------------
# VOTE CONFIRMATION PAGE
# --------------------------------------------------
@web_bp.get("/elections/<int:election_id>/confirmation")
def confirmation(election_id):
    user = current_user()

    if not user:
        return redirect(url_for("web.login_page"))

    election = Election.query.get_or_404(election_id)

    vote = Vote.query.filter_by(
        voter_id=user.id,
        election_id=election.id,
    ).first()

    if not vote:
        flash(
            "You have not voted in this election yet.",
            "warning",
        )

        return redirect(
            url_for(
                "web.election_details",
                election_id=election.id,
            )
        )

    return render_template(
        "voter/confirmation.html",
        election=election,
        user=user,
    )