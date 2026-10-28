"""Personalized AI Practice Plan service.

Generates 3 actionable practice activities tailored to the employee's
role, maturity level, and identified risk areas.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .. import models

ACTIVITY_CATALOG = {
    # Risk-driven activities
    "risk_customer_data": {
        "key": "risk_customer_data",
        "title": "Safe Prompt Redaction Challenge",
        "area": "Data Privacy & Customer Protection",
        "exercise": "Take 3 real customer communications from this week. Redact all customer PII (names, emails, account numbers) with anonymized placeholders before using external AI tools.",
        "criterion": "Draft 3 customer responses using AI with zero customer identifiable data entered into the prompt.",
    },
    "risk_confidential_data": {
        "key": "risk_confidential_data",
        "title": "Confidentiality Boundary Audit",
        "area": "Internal Security & Information Protection",
        "exercise": "Review your team's data classification guidelines. Create a personal quick-reference checklist of 5 data types that must never be shared with public AI models.",
        "criterion": "Document your checklist and verify your last 3 AI queries against it.",
    },
    "risk_unreviewed_output": {
        "key": "risk_unreviewed_output",
        "title": "Critical Verification Practice",
        "area": "Output Fact-Checking & Hallucination Prevention",
        "exercise": "Use AI to draft a technical or customer document. Identify and independently verify at least 2 factual claims, citations, or code logic assumptions.",
        "criterion": "Annotate every AI suggestion with a verified external source or test execution before sharing.",
    },
    "risk_policy_unaware": {
        "key": "risk_policy_unaware",
        "title": "AI Policy & Tool Alignment",
        "area": "Governance & Compliance",
        "exercise": "Locate and read your organization's official AI usage handbook. Identify which AI tools are approved for your specific department.",
        "criterion": "Confirm your list of approved tools and share any policy ambiguities with your manager.",
    },
    # Role-driven activities
    "role_engineering": {
        "key": "role_engineering",
        "title": "Test-Driven Prompt Scaffolding",
        "area": "Engineering: Unit Testing & Refactoring",
        "exercise": "Provide function signatures and edge-case specifications to an AI assistant to generate comprehensive unit test suites.",
        "criterion": "Achieve clean passing test coverage for at least one previously untested code path.",
    },
    "role_support": {
        "key": "role_support",
        "title": "Empathetic Tone Calibration",
        "area": "Support: Communication Quality",
        "exercise": "Use an AI prompt with explicit tone constraints (empathic, de-escalating, concise) to handle a complex customer inquiry.",
        "criterion": "Produce a customer-ready response draft that resolves the issue while sounding natural and human.",
    },
    "role_sales": {
        "key": "role_sales",
        "title": "Prospect Pain-Point Personalization",
        "area": "Sales: Outreach & Research",
        "exercise": "Feed public corporate filings into an AI tool and prompt it to extract 3 distinct business challenges relevant to your solution.",
        "criterion": "Send 2 personalized outreach emails referencing verified, specific company initiatives.",
    },
    "role_manager": {
        "key": "role_manager",
        "title": "Team AI Workflow Recipe",
        "area": "Management: Workflow Efficiency",
        "exercise": "Identify a recurring repetitive team process (e.g. sprint notes, ticket summaries). Write a step-by-step repeatable AI prompt template.",
        "criterion": "Share the documented prompt template with your team and measure time saved.",
    },
    # Maturity-driven activities
    "maturity_beginner": {
        "key": "maturity_beginner",
        "title": "Structured Prompting Fundamentals",
        "area": "Core Skills: RCTC Framework",
        "exercise": "Structure all prompts using Role, Context, Task, and Constraints (RCTC framework) rather than vague single-line queries.",
        "criterion": "Complete 3 distinct daily work tasks using structured multi-part prompts.",
    },
    "maturity_exploring": {
        "key": "maturity_exploring",
        "title": "Daily Workflow Integration Sprint",
        "area": "Core Skills: Workflow Integration",
        "exercise": "Integrate an approved AI tool into 2 different recurring daily workflows (e.g., meeting prep and drafting summaries).",
        "criterion": "Use AI consistently across 5 consecutive workdays for routine drafting.",
    },
    "maturity_practitioner": {
        "key": "maturity_practitioner",
        "title": "Peer Knowledge Sharing",
        "area": "Advanced: Team Enablement",
        "exercise": "Document a high-impact AI prompt or workflow you developed and review it for compliance and efficiency.",
        "criterion": "Publish or demo one reusable workflow recipe to team members.",
    },
    "maturity_leader": {
        "key": "maturity_leader",
        "title": "AI Risk & Quality Review",
        "area": "Leadership: Responsible AI Oversight",
        "exercise": "Perform an audit of how AI tools are used within your group, identifying opportunities for productivity and risk reduction.",
        "criterion": "Present 2 actionable recommendations to group leadership.",
    },
}


def select_activities_for_employee(job_role: str, maturity_level: str, risks: list[str]) -> list[dict]:
    """Deterministically selects 3 practice activities tailored to the employee."""
    selected_keys = []

    # 1. Prioritize addressing identified risks
    risk_mapping = {
        "customer_data_shared": "risk_customer_data",
        "confidential_data_shared": "risk_confidential_data",
        "unreviewed_output": "risk_unreviewed_output",
        "policy_unaware": "risk_policy_unaware",
    }
    for risk in risks:
        if risk in risk_mapping and risk_mapping[risk] not in selected_keys:
            selected_keys.append(risk_mapping[risk])
            if len(selected_keys) == 3:
                break

    # 2. Add role-specific activity if slots available
    if len(selected_keys) < 3:
        role_key = f"role_{job_role.lower()}" if job_role else ""
        if role_key in ACTIVITY_CATALOG and role_key not in selected_keys:
            selected_keys.append(role_key)

    # 3. Add maturity-specific activity if slots available
    if len(selected_keys) < 3:
        mat_key = f"maturity_{maturity_level.lower()}" if maturity_level else ""
        if mat_key in ACTIVITY_CATALOG and mat_key not in selected_keys:
            selected_keys.append(mat_key)

    # 4. Fill any remaining slots with core fundamentals
    fallbacks = ["maturity_beginner", "maturity_exploring", "role_manager"]
    for fb in fallbacks:
        if len(selected_keys) >= 3:
            break
        if fb not in selected_keys and fb in ACTIVITY_CATALOG:
            selected_keys.append(fb)

    return [ACTIVITY_CATALOG[k] for k in selected_keys[:3]]


def get_or_create_plan(m: models.Membership, db: Session, maturity_level: str, risks: list[str]) -> list[dict]:
    """Loads existing completion states from database or initializes for selected activities."""
    activities = select_activities_for_employee(m.job_role, maturity_level, risks)

    # Query existing item records for this membership
    existing_items = {
        item.activity_key: item
        for item in db.query(models.PracticePlanItem).filter_by(membership_id=m.id).all()
    }

    result = []
    for act in activities:
        key = act["key"]
        item = existing_items.get(key)
        result.append({
            "key": key,
            "title": act["title"],
            "area": act["area"],
            "exercise": act["exercise"],
            "criterion": act["criterion"],
            "completed": item.completed if item else False,
            "completed_at": item.completed_at.isoformat() if item and item.completed_at else None,
        })

    return result


def toggle_activity_status(m: models.Membership, activity_key: str, completed: bool, db: Session) -> dict:
    """Toggles or updates completion state for an activity belonging to the authenticated employee."""
    if activity_key not in ACTIVITY_CATALOG:
        raise ValueError(f"Unknown activity key: {activity_key}")

    item = (
        db.query(models.PracticePlanItem)
        .filter_by(membership_id=m.id, activity_key=activity_key)
        .first()
    )

    if not item:
        item = models.PracticePlanItem(
            membership_id=m.id,
            activity_key=activity_key,
            completed=completed,
            completed_at=datetime.now(timezone.utc) if completed else None,
        )
        db.add(item)
    else:
        item.completed = completed
        item.completed_at = datetime.now(timezone.utc) if completed else None

    db.commit()
    return {
        "activity_key": activity_key,
        "completed": item.completed,
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
    }
