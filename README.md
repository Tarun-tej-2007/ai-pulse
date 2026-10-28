# AI Pulse

AI Pulse helps enterprises assess and accelerate responsible AI adoption across departments and teams.

- **Employees** authenticate, choose their organization, and complete an adaptive AI diagnostic tailored to their role and seniority. Open-ended workplace scenarios are evaluated and scored by an AI model.
- **Each employee** receives an individual diagnostic report with maturity scores, detected risk indicators, recommended next steps, and a personalized **AI Practice Plan**.
- **Employees** maintain full sovereignty over their data with a one-click **Right to Delete**, immediately removing their answers, scores, and plan across all dashboards.
- **Company Leadership** accesses an executive dashboard of organizational AI maturity and top systemic risks, protected by **Small-Group Privacy** safeguards that withhold small team aggregates (< 5 completed assessments) to protect employee confidentiality.
- **Multi-Tenant Architecture**: Supports cross-company users (consultants, group-level advisors) who belong to multiple organizations with distinct organizational roles.

---

## Architecture & Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0, SQLite (with enforced foreign key constraints), PyJWT, Pydantic v2.
- **Frontend**: React 18, Vite 5, Vanilla CSS design system.
- **AI Engine**: Flexible provider integration supporting OpenAI-compatible chat completions (`AI_MODE=live`) and offline deterministic canned evaluation (`AI_MODE=mock`).

### Core Data Models

- **`Organization`**: Tenant boundary (e.g., Northwind Logistics, Bluepeak Retail).
- **`Department`**: Organizational unit within a tenant (e.g., Sales, Support, Engineering, HR).
- **`User`**: Global user account holding credentials and email.
- **`Membership`**: Scoped tenant relationship joining User to Organization, Department, Role (`admin` | `employee`), Job Role, and Seniority.
- **`Response`**: Individual diagnostic answer record linked to a Membership, storing question IDs, answers, AI scores, rationales, risk flags, and timestamps.
- **`PracticePlanItem`**: Personalized practice activity progress tracking linked to an employee Membership.

---

## Prerequisites & Supported Runtime Versions

- **Python**: **Python 3.12** is the officially targeted runtime version (matches [backend/Dockerfile](file:///backend/Dockerfile)).
  - *Note on Python 3.14*: Python 3.14 is currently pre-release/experimental. Several dependencies with C/Rust extensions (such as `pydantic-core`) lack pre-compiled wheels for 3.14 and fail source builds. Always run the backend in a Python 3.12 virtual environment (e.g., using `uv` or `python3.12 -m venv`).
- **Node.js**: Node 18.x or 20.x+ with `npm`.
- **Package Manager**: `uv` or standard `pip`.

---

## Configuration & Environment Variables

Create a `.env` file in the `backend/` directory by copying [backend/.env.example](file:///backend/.env.example):

```bash
cp backend/.env.example backend/.env
```

| Variable | Default Value | Description |
|---|---|---|
| `SECRET_KEY` | `ai-pulse-dev-secret` | Cryptographic secret for signing and verifying JWT tokens. |
| `DATABASE_URL` | `sqlite:///./aipulse.db` | SQLAlchemy database connection URI. |
| `AI_MODE` | `mock` | `mock` uses local deterministic responses; `live` calls external LLM endpoint. |
| `LLM_API_URL` | `""` | Chat completion endpoint URL (e.g. `https://api.openai.com/v1/chat/completions`). |
| `LLM_API_KEY` | `""` | Bearer API key for the LLM service. |
| `LLM_MODEL` | `""` | Target model name (e.g. `gpt-4o-mini`). |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated list of allowed CORS client origins. |

---

## Local Development Setup

### 1. Backend Setup

```bash
cd backend

# Create a virtual environment using Python 3.12
# With uv:
uv venv .venv --python 3.12
uv pip install -r requirements.txt --python .venv

# Or with standard python 3.12 venv:
# python3.12 -m venv .venv
# .\.venv\Scripts\Activate.ps1  (Windows) or source .venv/bin/activate (Linux/Mac)
# pip install -r requirements.txt

# Seed the database with demo accounts & baseline responses
.\.venv\Scripts\python -m app.seed

# Start the backend server on http://localhost:8000
.\.venv\Scripts\uvicorn app.main:app --reload
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the Vite development server on http://localhost:5173
npm run dev
```

---

## Automated Test Suites

Run the complete backend test suite using `pytest`:

```bash
cd backend
.\.venv\Scripts\python -m pytest
```

The automated suite consists of 40 tests covering:
- `tests/test_questions.py`: Seniority ranking, role filtering, manager questions at lead level, invalid seniority handling, boundary conditions.
- `tests/test_security.py`: Cross-tenant authorization, unauthorized organization selection, multi-tenant role switching, token requirements, forged/malformed tokens.
- `tests/test_privacy.py`: Small-group privacy thresholds (0, 1, 4, 5, 6 respondents), suppression behavior, unscored answers, cross-department isolation, deletion drop re-suppression.
- `tests/test_deletion.py`: Employee-controlled deletion, immediate dashboard synchronization, idempotency, cross-employee protection.
- `tests/test_ai_reliability.py`: AI response validation, markdown code block stripping, out-of-range score rejection, malformed JSON recovery, provider timeout rollback.
- `tests/test_practice_plan.py`: Personalized activity recommendation, completion state toggling, unassessed handling, deletion cascade, leadership dashboard privacy.
- `tests/test_api.py`: Baseline end-to-end integration flows.

---

## Verified Demo Accounts

All demo accounts use password: **`pulse123`**

| Email | Organization(s) | Role(s) | Description |
|---|---|---|---|
| `asha@northwind.test` | Northwind Logistics | Admin | Northwind executive leadership; views department dashboard & privacy protections. |
| `meera@bluepeak.test` | Bluepeak Retail | Admin | Bluepeak executive leadership. |
| `ravi@consult.test` | Northwind Logistics & Bluepeak Retail | Employee (Northwind) / Admin (Bluepeak) | Cross-tenant consultant; verifies multi-tenant role isolation upon org selection. |
| `priya@northwind.test` | Northwind Logistics | Employee (Support, Junior) | Support team member with seeded assessment answers and practice plan. |
| `dev@northwind.test` | Northwind Logistics | Employee (Engineering, Lead) | Engineering lead; verifies lead-level questions and diagnostic completion. |
| `vikram@northwind.test` | Northwind Logistics | Employee (Sales, Senior) | Sales team member with seeded baseline responses. |

---

# Assessment Engineering Report

### 1. Findings & Verified Defects

#### Defect 1: Alphabetical Seniority Comparison in Question Selection
- **Issue**: Seniority comparison in `backend/app/services/questions.py` relied on direct string inequality `seniority < q.get("min_seniority", "junior")`.
- **Impact**: In Python string comparison, `"lead" < "senior"` evaluates to `True` (`'l' < 's'`), and `"lead" < "mid"` evaluates to `True` (`'l' < 'm'`). Consequently, lead-level employees (like engineering leads or lead managers) were erroneously excluded from senior-level and mid-level questions, causing `test_lead_manager_gets_policy_questions` to fail.
- **Correction**: Replaced string comparison with an explicit numeric rank mapping (`junior: 1, mid: 2, senior: 3, lead: 4`). Invalid seniorities default safely to rank 0 (excluding restricted questions without crashing). Unknown question seniority requirements default to rank 99 to prevent accidental leakage.
- **Verification**: Verified by `tests/test_questions.py` (8 passing tests).

#### Defect 2: Critical Multi-Tenant Authorization Bypass in Dashboard Endpoint
- **Issue**: `backend/app/routes/dashboard.py` accepted an `org_id: int` query parameter and verified `m.role == "admin"`, but failed to verify whether `m.org_id == org_id`.
- **Impact**: An administrator belonging to Organization A could pass `?org_id=<Org B ID>` and read the full roster count, response metrics, and top risk flags of Organization B.
- **Correction**: Enforced server-side tenant scoping. The dashboard strictly operates on the active token's `m.org_id`. If an `org_id` parameter is supplied that differs from `m.org_id`, the server raises `HTTP 403 Forbidden: Access forbidden: cannot view another organization's dashboard`.
- **Verification**: Verified by `test_admin_cannot_see_other_org` in `tests/test_api.py` and `tests/test_security.py`.

#### Defect 3: Arbitrary Organization Token Generation in `/auth/select-org`
- **Issue**: `backend/app/routes/auth_routes.py` accepted any `org_id` and generated a signed JWT token without checking if the authenticated user possessed an active membership in that organization.
- **Impact**: Any authenticated user could forge a session for any tenant in the database.
- **Correction**: Added a database membership check: `db.query(models.Membership).filter_by(user_id=user.id, org_id=body.org_id).first()`. If no membership exists, raises `HTTP 403 Forbidden: Not a member of this organization`.
- **Verification**: Verified by `test_cannot_select_organization_without_membership` in `tests/test_security.py`.

#### Defect 4: Mathematical Flaw in Department Average Score Calculation
- **Issue**: `dashboard.py` computed department averages using `sum(scores) / len(dept_members)`.
- **Impact**: `scores` is a flat list of individual question points (e.g. 5 questions per employee, scale 1-5). Dividing total question points across all questions by the total number of registered employees (rather than completed respondents or question count) distorted the 1.0–5.0 scale and diluted scores whenever non-responding employees existed.
- **Correction**: Calculated average score per respondent (`sum(valid_scores) / len(valid_scores)`), then averaged across all completed respondents in that department (`sum(member_averages) / len(member_averages)`).
- **Verification**: Verified by `tests/test_privacy.py`.

#### Defect 5: Unvalidated AI Output and Code Fence Failures
- **Issue**: `backend/app/services/scoring.py` directly invoked `json.loads()` on raw LLM outputs without sanitization, range checks, or flag validation.
- **Impact**: LLMs wrapping responses in markdown blocks (```` ```json ... ``` ````) crashed with `JSONDecodeError`. Hallucinated scores (e.g. 7 or `"four"`) and invalid risk flags were written directly to database tables. Missing fields caused unhandled `KeyError`s.
- **Correction**: Implemented `_extract_json_string()` to strip code fences and extract valid JSON payloads. Added strict type and range validation (`1.0 <= score <= 5.0`), required non-empty `reason` strings, and filtered `flags` against an explicit whitelist of permitted categories (`customer_data_shared`, `confidential_data_shared`, `unreviewed_output`, `policy_unaware`). Invalid responses raise `AIValidationError` and trigger clean database rollbacks.
- **Verification**: Verified by `tests/test_ai_reliability.py` (8 passing tests).

#### Defect 6: Permissive Wildcard CORS and Insecure Password Storage
- **Issue**: `CORSMiddleware` in `main.py` allowed `*` origins, methods, and headers. Password verification in `auth.py` used unsalted SHA-256 with non-constant-time equality.
- **Impact**: Vulnerable to cross-origin abuse and timing attacks.
- **Correction**: Replaced wildcard CORS with explicit configurable origins from `CORS_ORIGINS`. Upgraded password verification to `hmac.compare_digest` with PBKDF2-HMAC-SHA256 salted hashes, while maintaining seamless backwards compatibility for existing demo hashes.
- **Verification**: Verified by `tests/test_security.py`.

---

### 2. Client Request Implementation

#### Requirement A: Small-Group Privacy
- **Implementation**:
  - Implemented on the server in `backend/app/routes/dashboard.py` before aggregates leave the API boundary.
  - Computes counts of **valid completed assessments**, not registered staff.
  - Enforces strict privacy threshold: `PRIVACY_THRESHOLD = 5`.
  - For departments with `< 5` completed assessments:
    - `suppressed: True`
    - `average_score: None`
    - `level: "Protected (< 5 responses)"` (or `"Not assessed"` if 0 responses)
    - `privacy_note: "Scores withheld to protect employee privacy (minimum 5 responses required)."`
    - Department-specific risk lists are omitted.
  - Aggregate company top risks only incorporate risk frequencies from qualifying departments meeting the privacy threshold, preventing single-respondent risk exposure.
  - The frontend renders an informative "Protected" badge and small-group privacy banner rather than implying a score of zero.
- **Testing**:
  - Verified with 0, 1, 4, 5, and 6 respondents in `tests/test_privacy.py`.
  - Verified independent threshold enforcement across departments and organizations.
- **Unresolved Client Questions**:
  - If a company consists entirely of departments with under 5 members, should an anonymized company-wide blended average be displayed, or should all department scores remain withheld?

#### Requirement B: Employee-Controlled Assessment Deletion
- **Implementation**:
  - Created authenticated endpoints `DELETE /diagnostic/me` and `DELETE /reports/me`.
  - Derives employee identity exclusively from the authenticated JWT session (`current_membership`). Clients cannot supply an arbitrary employee ID.
  - Executes an atomic database transaction deleting all `models.Response` and `models.PracticePlanItem` records for the membership.
  - Ensures immediate consistency: the employee report immediately returns `answered: 0`, and the leadership dashboard immediately updates respondent counts and scores.
  - Safe and idempotent: repeated deletion requests succeed cleanly with `deleted: 0`.
  - Frontend provides a confirmation modal with explanatory warning before executing deletion.
- **Testing**:
  - Verified by `tests/test_deletion.py` (deletion verification, idempotency, dashboard immediate decrement, cross-employee isolation).

---

### 3. Original Feature: AI Practice Plan

- **Problem Addressed**: Diagnostic reports provide employees with an AI maturity score and risk flags, but lack an immediate, practical pathway to improve their skills and address risky habits in their day-to-day work.
- **Solution Delivered**:
  - Built **AI Practice Plan**, an interactive feature delivering three tailored, practical micro-exercises based on the employee's diagnostic answers:
    1. **Risk Mitigation (Top Priority)**: If risks are detected (e.g. `customer_data_shared`, `confidential_data_shared`, `unreviewed_output`), activities target specific redaction, verification, or policy practices.
    2. **Role-Specific Workflows**: Hands-on exercises tailored to engineering (test-driven prompt scaffolding), support (tone calibration), sales (pain-point personalization), or management (workflow templates).
    3. **Maturity Level Progression**: Targeted progression exercises based on current maturity level (Beginner, Exploring, Practitioner, Leader).
  - Each activity includes: Title, Skill/Focus Area tag, Practical Exercise description, Completion Criterion, and interactive completion state.
  - Deterministic recommendation engine in `backend/app/services/practice_plan.py` eliminates unnecessary LLM cost and latency.
  - Scoped strictly to the employee: leadership cannot view individual employee plans or progress.
  - When an employee deletes their assessment, practice plan records are automatically purged.
- **Testing**: Verified by `tests/test_practice_plan.py` (generation, completion toggling, unassessed handling, deletion cascading).

---

### 4. AI Tool Usage

- **Tools Used**: Antigravity AI assistant with automated terminal execution and AST code navigation.
- **Verification Methodology**: Every code modification was verified by running targeted unit tests, running full automated pytest suites, and building the frontend bundle. No test was claimed to pass without inspecting real execution output.
- **Real Example of Incorrect AI Assumption**:
  - During initial environment setup, the AI tool attempted to compile `pydantic-core` under Python 3.14 with `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1`.
  - When the build failed due to missing C-API symbols (`PyUnicode_New`), the compiler help text suggested replacing `PyUnicode_New` with `PySlice_New`. An unverified automated agent might have attempted patching source code based on this hint.
  - However, investigating the root cause revealed that Python 3.14 fundamentally changed internal C-API representations and PyO3 0.22 does not support 3.14. The correct engineering solution was recognizing that the project targets Python 3.12 (as specified in `backend/Dockerfile`) and provisioning a Python 3.12 virtual environment via `uv`, immediately resolving all binary wheel compatibility issues.
  - Additionally, during `test_privacy.py` test authoring, the AI assumed the Support department had 0 initial responses, overlooking that Priya Nair was already seeded in Support with responses (average score 2.5). When 5 new test users with score 3.0 were added, the department average evaluated to 2.92 instead of 3.0. The test was corrected to explicitly reset responses prior to testing isolated count thresholds.

---

### 5. Deliberately Left Out & Recommended Next Steps

1. **Database Migrations (Alembic)**: Currently tables are generated via `Base.metadata.create_all()`. For a production rollout, an Alembic migration pipeline should be introduced to version schema changes.
2. **PostgreSQL Production Configuration**: SQLite is currently used for local and pilot testing. Production deployment should configure PostgreSQL with connection pooling.
3. **SSO / Enterprise Identity**: Current authentication uses local credentials with PBKDF2 password hashing. Enterprise rollout should integrate SAML/OIDC (Okta, Azure AD, Google Workspace).
4. **Audit Logging Service**: Add a dedicated audit event log for administrative access and deletion requests (recording actor and timestamp without logging private answer content).

---

### 6. Verification Results

- **Automated Backend Test Suite**:
  - Command: `python -m pytest`
  - Result: **40 passed, 1 warning (Starlette internal) in 33.11s**.
- **Frontend Production Build**:
  - Command: `npm run build`
  - Result: **Clean build, 37 modules transformed in 1.74s, 0 errors**.
- **Manual End-to-End Flows Verified**:
  - Asha Rao (`asha@northwind.test`): Admin login -> Northwind dashboard -> small-group privacy active on protected departments -> verified cross-tenant dashboard access to Bluepeak returns 403.
  - Priya Nair (`priya@northwind.test`): Employee login -> report view -> interactive practice plan completion toggling -> Right to Delete execution -> immediate dashboard reduction.
  - Ravi Kapoor (`ravi@consult.test`): Multi-tenant switching between Northwind (employee) and Bluepeak (admin).
