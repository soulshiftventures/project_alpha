"""
Operator Interface - Flask Application.

Lightweight local web interface for Project Alpha operator control.

Usage:
    python3 ui/app.py
    # or
    PYTHONPATH=. python3 ui/app.py

Then visit http://localhost:5000
"""

import os
import sys

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from flask import Flask, render_template, request, jsonify, redirect, url_for
from ui.services import get_operator_service, GoalSubmission, OperatorService

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "project-alpha-dev-key")

# Get service instance
def get_service() -> OperatorService:
    """Get the operator service (lazy init on first request)."""
    return get_operator_service()


# =============================================================================
# Template Context
# =============================================================================

@app.context_processor
def inject_globals():
    """Inject global template variables."""
    return {
        "app_name": "Project Alpha",
        "version": "0.1.0",
    }


# =============================================================================
# Home / System Overview
# =============================================================================

@app.route("/")
def home():
    """System overview / home page."""
    service = get_service()
    status = service.get_system_status()
    recent_events = service.get_events(limit=10)
    recent_decisions = service.get_recent_decisions(limit=5)

    return render_template(
        "home.html",
        status=status.to_dict(),
        recent_events=recent_events,
        recent_decisions=recent_decisions,
    )


@app.route("/api/status")
def api_status():
    """API: Get system status."""
    service = get_service()
    status = service.get_system_status()
    return jsonify(status.to_dict())


# =============================================================================
# Portfolio View
# =============================================================================

@app.route("/portfolio")
def portfolio():
    """Portfolio view - list businesses/initiatives."""
    service = get_service()
    businesses = service.get_portfolio()

    return render_template(
        "portfolio.html",
        businesses=[b.to_dict() for b in businesses],
    )


@app.route("/api/portfolio")
def api_portfolio():
    """API: Get portfolio."""
    service = get_service()
    businesses = service.get_portfolio()
    return jsonify([b.to_dict() for b in businesses])


@app.route("/portfolio/<business_id>")
def portfolio_detail(business_id: str):
    """Portfolio detail view."""
    service = get_service()
    business = service.get_business(business_id)

    if not business:
        return render_template("error.html", message="Business not found"), 404

    return render_template(
        "portfolio_detail.html",
        business=business.to_dict(),
    )


# =============================================================================
# Goal / Request Submission
# =============================================================================

@app.route("/goals", methods=["GET"])
def goals():
    """Goal submission page."""
    service = get_service()
    history = service.get_orchestration_history(limit=10)

    return render_template(
        "goals.html",
        history=history,
    )


@app.route("/goals/submit", methods=["POST"])
def submit_goal():
    """Submit a new goal."""
    service = get_service()

    # Get form data
    objective = request.form.get("objective", "").strip()
    if not objective:
        return render_template("goals.html", error="Objective is required", history=[])

    submission = GoalSubmission(
        objective=objective,
        business_id=request.form.get("business_id") or None,
        stage=request.form.get("stage") or None,
        priority=request.form.get("priority", "medium"),
        notes=request.form.get("notes") or None,
        requester="principal",
    )

    result = service.submit_goal(submission)

    # Redirect to plan view if we have one
    if result.execution_plan:
        return redirect(url_for("plan_detail", request_id=result.request_id))

    return redirect(url_for("goals"))


@app.route("/api/goals", methods=["POST"])
def api_submit_goal():
    """API: Submit a goal."""
    service = get_service()
    data = request.get_json() or {}

    objective = data.get("objective", "").strip()
    if not objective:
        return jsonify({"error": "Objective is required"}), 400

    submission = GoalSubmission(
        objective=objective,
        business_id=data.get("business_id"),
        stage=data.get("stage"),
        priority=data.get("priority", "medium"),
        notes=data.get("notes"),
        requester="principal",
    )

    result = service.submit_goal(submission)
    return jsonify(result.to_dict())


# =============================================================================
# Execution Plan View
# =============================================================================

@app.route("/plans")
def plans():
    """List execution plans."""
    service = get_service()
    recent_plans = service.get_recent_plans(limit=20)

    return render_template(
        "plans.html",
        plans=recent_plans,
    )


@app.route("/plans/<request_id>")
def plan_detail(request_id: str):
    """Execution plan detail view."""
    service = get_service()
    plan_data = service.get_execution_plan(request_id)

    if not plan_data:
        return render_template("error.html", message="Plan not found"), 404

    return render_template(
        "plan_detail.html",
        request_id=request_id,
        plan=plan_data,
    )


@app.route("/api/plans")
def api_plans():
    """API: List execution plans."""
    service = get_service()
    plans = service.get_recent_plans(limit=50)
    return jsonify(plans)


@app.route("/api/plans/<request_id>")
def api_plan_detail(request_id: str):
    """API: Get execution plan detail."""
    service = get_service()
    plan = service.get_execution_plan(request_id)
    if not plan:
        return jsonify({"error": "Plan not found"}), 404
    return jsonify(plan)


# =============================================================================
# Approval Queue
# =============================================================================

@app.route("/approvals")
def approvals():
    """Approval queue view."""
    service = get_service()
    pending = service.get_pending_approvals()
    history = service.get_approval_history(limit=20)

    return render_template(
        "approvals.html",
        pending=pending,
        history=history,
    )


@app.route("/approvals/<record_id>/approve", methods=["POST"])
def approve(record_id: str):
    """Approve a pending request."""
    service = get_service()
    success = service.approve_request(record_id, approver="principal")

    if request.headers.get("Accept") == "application/json":
        return jsonify({"success": success})

    return redirect(url_for("approvals"))


@app.route("/approvals/<record_id>/deny", methods=["POST"])
def deny(record_id: str):
    """Deny a pending request."""
    service = get_service()
    reason = request.form.get("reason", "Denied by operator")
    success = service.deny_request(record_id, reason, denier="principal")

    if request.headers.get("Accept") == "application/json":
        return jsonify({"success": success})

    return redirect(url_for("approvals"))


@app.route("/api/approvals")
def api_approvals():
    """API: Get pending approvals."""
    service = get_service()
    pending = service.get_pending_approvals()
    return jsonify(pending)


@app.route("/api/approvals/<record_id>/approve", methods=["POST"])
def api_approve(record_id: str):
    """API: Approve a request."""
    service = get_service()
    success = service.approve_request(record_id, approver="principal")
    return jsonify({"success": success})


@app.route("/api/approvals/<record_id>/deny", methods=["POST"])
def api_deny(record_id: str):
    """API: Deny a request."""
    service = get_service()
    data = request.get_json() or {}
    reason = data.get("reason", "Denied by operator")
    success = service.deny_request(record_id, reason, denier="principal")
    return jsonify({"success": success})


# =============================================================================
# Job Monitor
# =============================================================================

@app.route("/jobs")
def jobs():
    """Job monitor view."""
    service = get_service()
    status_filter = request.args.get("status")
    job_list = service.get_jobs(status=status_filter, limit=50)
    stats = service.get_job_stats()

    return render_template(
        "jobs.html",
        jobs=job_list,
        stats=stats,
        current_status=status_filter,
    )


@app.route("/jobs/<job_id>")
def job_detail(job_id: str):
    """Job detail view."""
    service = get_service()
    job = service.get_job(job_id)

    if not job:
        return render_template("error.html", message="Job not found"), 404

    return render_template(
        "job_detail.html",
        job=job,
    )


@app.route("/jobs/<job_id>/cancel", methods=["POST"])
def cancel_job(job_id: str):
    """Cancel a running job."""
    service = get_service()
    success = service.cancel_job(job_id)

    if request.headers.get("Accept") == "application/json":
        return jsonify({"success": success})

    return redirect(url_for("jobs"))


@app.route("/api/jobs")
def api_jobs():
    """API: List jobs."""
    service = get_service()
    status = request.args.get("status")
    jobs = service.get_jobs(status=status, limit=100)
    return jsonify(jobs)


@app.route("/api/jobs/<job_id>")
def api_job_detail(job_id: str):
    """API: Get job detail."""
    service = get_service()
    job = service.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/jobs/stats")
def api_job_stats():
    """API: Get job statistics."""
    service = get_service()
    stats = service.get_job_stats()
    return jsonify(stats)


# =============================================================================
# Event Log View
# =============================================================================

@app.route("/events")
def events():
    """Event log view."""
    service = get_service()
    event_type = request.args.get("type")
    severity = request.args.get("severity")
    event_list = service.get_events(event_type=event_type, severity=severity, limit=100)
    counts = service.get_event_counts()

    return render_template(
        "events.html",
        events=event_list,
        counts=counts,
        current_type=event_type,
        current_severity=severity,
    )


@app.route("/api/events")
def api_events():
    """API: Get events."""
    service = get_service()
    event_type = request.args.get("type")
    severity = request.args.get("severity")
    limit = int(request.args.get("limit", 100))
    events = service.get_events(event_type=event_type, severity=severity, limit=limit)
    return jsonify(events)


@app.route("/api/events/counts")
def api_event_counts():
    """API: Get event counts."""
    service = get_service()
    counts = service.get_event_counts()
    return jsonify(counts)


@app.route("/api/events/errors")
def api_errors():
    """API: Get recent errors."""
    service = get_service()
    errors = service.get_errors(limit=50)
    return jsonify(errors)


# =============================================================================
# Backends View
# =============================================================================

@app.route("/backends")
def backends():
    """Available backends view."""
    service = get_service()
    backend_list = service.get_backends()
    runtime_stats = service.get_runtime_stats()

    return render_template(
        "backends.html",
        backends=backend_list,
        stats=runtime_stats,
    )


@app.route("/api/backends")
def api_backends():
    """API: Get available backends."""
    service = get_service()
    backends = service.get_backends()
    return jsonify(backends)


# =============================================================================
# Error Handlers
# =============================================================================

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    return render_template("error.html", message="Page not found"), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error"}), 500
    return render_template("error.html", message="Internal server error"), 500


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"

    print(f"""
================================================================================
  Project Alpha - Operator Interface
================================================================================

  Starting server on http://localhost:{port}

  Routes:
    /             - System Overview
    /portfolio    - Portfolio View
    /goals        - Goal Submission
    /plans        - Execution Plans
    /approvals    - Approval Queue
    /jobs         - Job Monitor
    /events       - Event Log
    /backends     - Available Backends

  API endpoints available at /api/*

  Press Ctrl+C to stop.
================================================================================
""")

    app.run(host="0.0.0.0", port=port, debug=debug)
