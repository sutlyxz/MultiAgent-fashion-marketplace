# Clothify Fashion Marketplace

Clothify is a full-stack fashion marketplace web application built with FastAPI, PostgreSQL/SQLAlchemy, and React (TypeScript + Vite).

---

## 1. Project Overview & Architecture

The repository consists of:

- **Backend (`backend/`):** FastAPI application providing REST APIs for product catalog, user authentication, checkout, order fulfillment & tracking, seller management, simulated payment verification, and in-app AI customer/seller support ticketing.
  - PostgreSQL persistence with SQLAlchemy ORM and Alembic database migrations.
  - Comprehensive backend unit and integration test suite in `backend/tests/`.
- **Frontend (`frontend/`):** Luxury and modern responsive web storefront built with React 18, TypeScript, Tailwind CSS, and Vite.
  - Buyer shopping experience (catalog browsing, cart, checkout with slip upload / simulated payment, order history).
  - Seller Studio (product listing management, order fulfillment, shipment tracking, customer support claims).
- **Protected Application Tests (`tests/`):** Dedicated root-level unit tests for database connection lifecycle and payment verification logic (`test_database_connection.py` and `test_payment_verification.py`).
- **Markdown-Based Engineering Workflow:** Structured operational methodology governed by `workflow.md` and role specifications in `.agents/skills/*.md`.
- **Run History (`.agent_runs/`):** Historical execution records preserved for auditing purposes.

---

## 2. Markdown Workflow Specification

Engineering tasks, refactoring, and audits follow the Markdown-based workflow documented in:

- **`workflow.md`:** The Master Workflow governing the staged development cycle:
  1. Intake & Clarification
  2. PM Analysis & Requirements Specification
  3. Architecture Design & Technical Planning
  4. Implementation & Pair Programming
  5. Integration Review & Code Inspection
  6. QA Verification & Test Gate
  7. Security Review & Compliance Gate
  8. Human Review & Approval Gate
  9. Final Handoff & Documentation

- **Role Specifications (`.agents/skills/`):**
  - `.agents/skills/pm-agent.md`: Product Manager role directives and scope definition.
  - `.agents/skills/architect-agent.md`: Software Architect role directives, data models, and API contracts.
  - `.agents/skills/frontend-developer.md`: Frontend engineering directives and UI/UX standards.
  - `.agents/skills/backend-developer.md`: Backend engineering directives, data safety, and API standards.
  - `.agents/skills/qa-agent.md`: Quality Assurance verification protocols and regression testing criteria.
  - `.agents/skills/security-agent.md`: Security compliance, IDOR defense, and input validation checks.

> **Operational Note:** Role instructions in `.agents/skills/*.md` serve as human-readable engineering guidelines and role prompts. They are executed through collaborative pair programming and manual verification, rather than autonomous unverified CLI execution.

---

## 3. Installation & Setup

### Backend Setup

1. Create and activate a Python virtual environment:
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Install Python dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
3. Configure environment variables in `.env` (refer to `backend/app/config.py` for settings such as `DATABASE_URL`, `JWT_SECRET`, `ENVIRONMENT`, and `PAYMENT_RECIPIENT_ACCOUNT`. In production environments, `JWT_SECRET` is strictly required and must be at least 32 characters long with high entropy; `SECRET_KEY` is also accepted as an alias).

4. Run database migrations:
   ```cmd
   cd backend
   alembic upgrade head
   ```

5. Start the backend development server:
   ```cmd
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```cmd
   cd frontend
   npm install
   ```
2. Start the Vite development server:
   ```cmd
   npm run dev
   ```
3. Build for production:
   ```cmd
   npm run build
   ```

---

## 4. Running Tests

The test suite covers the complete application logic across both root application tests and backend modules:

### 1. Root Application Tests
Tests verifying database engine configuration handling and fallback payment verification:
```cmd
.venv\Scripts\pytest.exe tests/test_database_connection.py tests/test_payment_verification.py -v
```

### 2. Backend Test Suite
Comprehensive suite covering auth, products, orders, seller studio, shipments, seed data, and simulated payments:
```cmd
.venv\Scripts\pytest.exe backend/tests/ -q
```

### 3. Combined Application Test Run
Run both suites with PYTHONPATH configured:
```powershell
$env:PYTHONPATH="backend"
.venv\Scripts\pytest.exe backend/tests/ tests/test_database_connection.py tests/test_payment_verification.py -v
```
