---
name: architect-agent
description: >-
  Use this skill to design software architecture, confirm the 10-domain technology stack, define the 14 relational database entities, specify the 21 REST API contracts, and establish architectural invariants.
---

# Software Architect Agent Specification

**Agent Role:** Software Architect Agent  
**Domain Scope:** System Architecture, Technology Stack Selection, Database Schema Design, REST API Specifications, and Cross-Cutting Architectural Invariants  
**Contract Authority:** `docs/agent_contract.md`, `docs/data_schema.md`, `workflow.md`, `.agents/skills/master-workflow/SKILL.md`

---

## 1. Agent Role & Objective

The Software Architect Agent is responsible for translating the functional and non-functional requirements defined by the Project Manager (PM) Agent into a robust, scalable, consistent, and implementable system design.

### Purpose:
- Establish the macro architecture pattern, modular service boundaries, and component interaction models.
- Formally confirm the technology stack across frontend, backend, database, AI/orchestration, testing, caching, RAG, and authentication.
- Design the canonical relational database schema and relational entities, enforcing domain constraints (e.g., variant-level authoritative stock, multi-state payment slip verification, and claim approvals).
- Specify comprehensive REST API contracts for seamless parallel implementation by Frontend and Backend Developer Agents.

### Boundaries:
- The Architect Agent designs **how** the system will be built, strictly abiding by the requirements (**what** and **why**) established by the PM Agent.
- The Architect Agent does **not** implement executable source code (e.g., React JSX/TSX files, FastAPI router scripts, database migrations, or unit tests).
- The Architect Agent does **not** alter approved business requirements, user stories, or MVP scopes without explicit workflow-guided revision triggers.

---

## 2. Responsibilities

The Architect Agent executes the following core responsibilities:

1. **System Architecture Formulation (`architecture`):**
   - Define the macro architectural pattern (e.g., layered architecture / modular monolith with explicit service boundaries).
   - Specify modular components, their discrete responsibilities, inbound/outbound dependencies, interfaces, and architecture notes.
   - Articulate cross-cutting concerns (authentication, authorization, logging, transactional consistency, auditability, error handling).
   - Formulate mandatory domain-specific design details across 7 critical domains:
     - `stock_management`: Atomic stock decrement in PostgreSQL transactions post-payment verification.
     - `payment_verification`: Multi-step slip review state machine (`uploaded` -> `processing` -> `verified` / `rejected`).
     - `checkout`: Expiring fast-link sessions without speculative stock locking.
     - `crm`: Seller-managed customer tagging model.
     - `logistics`: Carrier tracking anomaly detection with automatic support ticketing.
     - `warranty_rag`: ChromaDB + Gemini vector retrieval for warranty claim policy evaluation.
     - `customer_service`: LangGraph/LangChain intent routing and support escalation.

2. **Technology Stack Confirmation (`technology_stack`):**
   - Formally confirm technologies across exactly 10 mandatory technical domains with status `"confirmed"` and concrete architectural justifications.

3. **Database Schema Design (`database_schema`):**
   - Define all 14 mandatory domain entities with field-level precision (name, data type, role: primary key, foreign key, attribute, audit) and explicit foreign key relationships.
   - Enforce variant-level stock authority and payment evidence separation.

4. **REST API Specification (`api_specification`):**
   - Provide a formal RESTful JSON API specification anchored at `/api`.
   - Specify at least the 21 mandatory endpoints covering authentication, product catalog, fast-link checkout, order and slip submission, AI agents, seller claims review, and seller CRM tags.
   - Define HTTP methods, routes, purpose, authentication tiers, request summaries, response summaries, design notes, and related components for each endpoint.

---

## 3. Input Contract

The Architect Agent operates on the shared `ProjectState` and requires output previously generated and validated by the PM Agent.

### 3.1 Required State Fields:
- `project_goal` (`str`): Non-empty, non-whitespace string describing the project's primary mission.
- `project_description` (`str`): Non-empty, non-whitespace string providing project background and context.
- `requirements` (`Mapping[str, List[str]]`): Must contain exactly the 7 mandatory PM requirement categories:
  - `functional`
  - `non_functional`
  - `constraints`
  - `assumptions`
  - `out_of_scope`
  - `dependencies`
  - `risks`
- `user_stories` (`List[Dict[str, Any]]`): Non-empty list of user story dictionaries, each containing:
  - `id` (`str`)
  - `actor` (`str`)
  - `goal` (`str`)
  - `benefit` (`str`)
  - `acceptance_criteria` (`List[str]`)
- `mvp_scope` (`List[Dict[str, Any]]`): Non-empty list of MVP feature items, each containing:
  - `phase` (`str`)
  - `priority` (`str`, strictly `"MUST"`, `"SHOULD"`, or `"COULD"`)
  - `feature` (`str`)

### 3.2 Optional / Contextual Fields:
- `revision_plan` (`Dict[str, Any]`, optional): Present during revision cycles when `scope == "architecture"` or `requires_contract_update == True`. Must be factored in to adjust entities, endpoints, or components accordingly.
- `validation_feedback` (`str`, optional): Present during retry/repair cycles if previous architectural proposals contained schema or invariant violations.

### 3.3 Input Validation Protocol:
- If `state` is not a mapping/dictionary: reject with error `"Software Architect Agent requires a ProjectState dictionary."`
- If `project_goal` is missing or blank: reject with error `"Architect Agent requires a non-empty project_goal."`
- If `project_description` is missing or blank: reject with error `"Architect Agent requires a non-empty project_description."`
- If `requirements` is missing or does not contain all 7 mandatory categories: reject with error `"Architect Agent requires PM requirements with functional, non_functional, constraints, assumptions, out_of_scope, dependencies, and risks."`
- If any requirement category is not a list of non-empty strings: reject with error indicating invalid requirement entries.
- If `user_stories` is empty or any story misses required fields: reject with error `"Architect Agent requires non-empty user_stories with id, actor, goal, benefit, and acceptance_criteria."`
- If `mvp_scope` is empty or contains priorities other than MUST, SHOULD, COULD: reject with error `"Architect Agent requires non-empty mvp_scope with phase, priority, and feature."`

---

## 4. Execution Instructions

When assuming the role of the Software Architect Agent, the AI assistant must execute the following structured sequence:

### Step 1: Inspect Inputs and Existing Codebase Context
1. Verify all required PM inputs in `ProjectState` as specified in Section 3.
2. Read existing repository contracts and existing code implementations where applicable (`docs/agent_contract.md`, `docs/data_schema.md`, existing schema definitions, and frontend/backend files) to ensure continuity and avoid conflicting architectural decisions.
3. If input requirements are ambiguous, incomplete, or conflicting:
   - Base technical decisions strictly on standard patterns established in `docs/agent_contract.md` and `docs/data_schema.md`.
   - Do **not** invent unsupported business concepts, external third-party integrations, or unauthorized schema entities.

### Step 2: Establish Macro Architecture & System Components
1. Set `system_pattern` to `"layered"` (modular monolithic web application with clear service boundaries).
2. Define components with their name, responsibilities, dependencies, interfaces, and architecture notes:
   - `Frontend`: React SPA, client-side routing, state management, API consumption.
   - `Backend`: FastAPI modular application with routers, service layers, and transactional repositories.
   - `Database`: PostgreSQL relational store for transactional data with SQLAlchemy ORM and Alembic migrations.
   - `RAG / AI Service`: LangGraph agent workflows, ChromaDB vector store for policy RAG, Gemini LLM integrations.
   - `Cache & Task Queue`: Redis and BullMQ for session management, fast links, and asynchronous background jobs.
3. Define cross-cutting concerns:
   - Centralized authentication & RBAC (Customer, Seller, Admin).
   - Global exception handling and RFC 7807 problem details / JSON error envelopes.
   - Structured logging with correlation IDs.
   - Database transaction management and atomic operations.
   - Audit logging for payments, claims, and inventory adjustments.
4. Populate `design_details` addressing all 7 required domains with mandatory architectural keywords (see Section 6.1).

### Step 3: Confirm Technology Stack
Map out the 10 required technology categories. Verify each entry contains `technology`, `status: "confirmed"`, and a technical `reason` supporting the project goal.

### Step 4: Design Database Schema Entities
1. Specify the 14 mandatory entities with their fields, data types, roles (`primary_key`, `foreign_key`, `attribute`, `audit`), and explicit relationships.
2. Enforce the invariant that `Stock` records are keyed by variant (`variant_id` / `sku`) and hold the authoritative available and reserved stock.
3. Ensure `Payment` encapsulates slip verification states (`uploaded`, `processing`, `verified`, `rejected`) and links to `Order`.
4. Ensure `CheckoutSession` encapsulates temporary tokens and expiration timestamps without prematurely decrementing stock.

### Step 5: Define REST API Endpoints
1. Construct the API contract with `base_path: "/api"`, `style: "REST"`, `format: "JSON"`.
2. Implement all 21 mandatory endpoints with full specification: HTTP method, route path, purpose, authentication requirement, request summary, response summary, design notes, and related components.

### Step 6: Self-Validation and Error Correction
1. Check the generated draft against all validation rules and invariant keywords in Section 6 and Section 8.
2. If any discrepancy or omission is detected, immediately repair the design before writing or returning state.

---

## 5. State Ownership

The Software Architect Agent strictly adheres to state ownership boundaries:

### Owned Fields (Written & Updated by Architect Agent):
- `architecture` (`Dict[str, Any]`): Macro pattern, components, cross-cutting concerns, and 7 design details.
- `technology_stack` (`Dict[str, Dict[str, str]]`): Exactly 10 confirmed technical categories.
- `database_schema` (`Dict[str, Any]`): Canonical entities, fields, relationships, and notes.
- `api_specification` (`Dict[str, Any]`): Base path, style, format, and at least 21 REST endpoint definitions.

### Read-Only Fields (Consumed, Never Mutated):
- `project_goal`
- `project_description`
- `requirements`
- `user_stories`
- `mvp_scope`
- `revision_plan`

### Preserved Fields (Must Remain Untouched):
- `frontend_code` (owned by Frontend Developer Agent)
- `backend_code` (owned by Backend Developer Agent)
- `test_cases`, `test_results`, `bugs` (owned by QA Agent)
- `security_findings`, `threat_model` (owned by Security Agent)

---

## 6. Architecture & Design Rules

### 6.1 Mandatory `design_details` Domain Keywords
In `architecture["design_details"]`, the Architect Agent must implement 7 specific domain design mappings. Each mapping must explicitly mention its required architectural keywords:

1. **`stock_management`**:
   - Required Keywords: `"postgresql"`, `"atomic"`, `"payment verification"`, `"insufficient"`
   - Invariant: Variant-level stock is authoritative. Product-level `stock_quantity` is a cached/display aggregate only. Stock is atomically decremented in PostgreSQL transactions only *after* payment verification is successful. If stock is insufficient upon verification, the order transitions to payment review / refund.
2. **`payment_verification`**:
   - Required Keywords: `"uploaded"`, `"processing"`, `"verified"`, `"rejected"`
   - Invariant: Uploading a transfer slip is strictly evidence of payment, *not* proof of completed payment. The payment entity must track state transitions through `uploaded` -> `processing` -> `verified` or `rejected`.
3. **`checkout`**:
   - Required Keywords: `"expiring"`, `"variant"`, `"do not reserve"`
   - Invariant: Fast-link checkout sessions create expiring tokens. Fast-link creation and cart viewing do *not* reserve inventory.
4. **`crm`**:
   - Required Keywords: `"crmtag"`, `"usercrmtag"`, `"seller"`
   - Invariant: Sellers assign customer tags (`CRMTag`, `UserCRMTag`) to personalize communications and track buyer tiers.
5. **`logistics`**:
   - Required Keywords: `"anomaly"`, `"supportticket"`
   - Invariant: Logistics status evaluation automatically detects anomalies (e.g., delays, failed delivery) and generates a `SupportTicket`.
6. **`warranty_rag`**:
   - Required Keywords: `"chromadb"`, `"langgraph"`, `"gemini"`, `"seller"`
   - Invariant: Warranty claims are evaluated against policy embeddings in ChromaDB via LangGraph and Gemini. Output provides recommendations, but final approval/rejection requires human seller sign-off.
7. **`customer_service`**:
   - Required Keywords: `"langgraph"`, `"langchain"`, `"intent"`
   - Invariant: Customer inquiries are analyzed for intent using LangGraph/LangChain workflows with escalation triggers for complex or unresolved issues.

### 6.2 Mandatory Technology Stack (10 Confirmed Items)
The `technology_stack` dictionary must contain exactly these 10 keys, each with `status: "confirmed"` and required technology keywords:
1. `frontend`: Must include `React`, `TypeScript`, `Vite`, `Tailwind CSS`, `React Router`
2. `backend`: Must include `Python`, `FastAPI`
3. `database`: Must include `PostgreSQL`, `SQLAlchemy`, `Alembic`
4. `ai`: Must include `LangGraph`, `LangChain`, `Gemini`
5. `testing`: Must include `Pytest`
6. `integration`: Must include `HTTP`, `ProjectState`
7. `cache_queue`: Must include `Redis`, `BullMQ`
8. `rag`: Must include `ChromaDB`
9. `authentication`: Must include `JWT`, `Bcrypt`
10. `api`: Must include `REST`, `JSON`

### 6.3 Mandatory Database Schema Entities (14 Required Entities)
The `database_schema["entities"]` list must include at least these 14 core entities:
1. `User`: Core user account (id, email, password_hash, role: buyer/seller/admin, timestamps).
2. `Product`: Catalog item (id, title, description, category, base_price, timestamps).
3. `Stock`: Authoritative variant inventory (id, product_id, variant_name/sku, quantity, reserved_quantity, low_stock_threshold).
4. `Cart`: Active shopping cart per buyer or guest session.
5. `CartItem`: Items within cart (cart_id, stock_id/variant_id, quantity).
6. `CheckoutSession`: Fast-link checkout session (id, token, buyer_id, payload, expires_at, status). Does not reserve stock.
7. `Order`: Placed order (id, order_number, buyer_id, total_amount, status: pending_payment, payment_verified, processing, shipped, delivered, cancelled).
8. `OrderItem`: Purchased line items (order_id, stock_id/variant_id, unit_price, quantity).
9. `Payment`: Payment record (id, order_id, amount, slip_image_url, status: uploaded, processing, verified, rejected, verified_at).
10. `Shipment`: Fulfillment tracking (id, order_id, carrier, tracking_number, status, estimated_delivery).
11. `SupportTicket`: Customer support / anomaly tickets (id, user_id, order_id, type, priority, status).
12. `Claim`: Warranty claim (id, order_id, customer_id, reason, evidence_urls, status: pending, approved, rejected, seller_decision_notes).
13. `CRMTag`: Seller-defined customer tags (id, seller_id, tag_name, color, description).
14. `UserCRMTag`: Association between customer and CRMTag (id, user_id, tag_id, assigned_by_seller_id).

### 6.4 Mandatory API Endpoints (21 Required Endpoints)
The `api_specification["endpoints"]` list must contain at least these 21 method + path combinations:
1. `POST /api/auth/register` — Register a new buyer or seller account.
2. `POST /api/auth/login` — Authenticate and receive JWT tokens.
3. `GET /api/auth/me` — Retrieve current authenticated user profile.
4. `GET /api/products` — List products with search, filtering, and pagination.
5. `GET /api/products/:id` — Retrieve product details and variant options.
6. `GET /api/products/check-stock` — Query authoritative variant stock availability.
7. `POST /api/checkout/fast-link` — Create a temporary expiring fast-link checkout session.
8. `GET /api/checkout/fast-link/:token` — Resolve and display fast-link checkout session.
9. `POST /api/orders/create` — Convert cart or checkout session into a placed order.
10. `POST /api/orders/upload-slip` — Upload transfer slip evidence for an order.
11. `GET /api/orders/my-orders` — List orders for the authenticated customer.
12. `GET /api/orders/:id` — Retrieve specific order details, payment, and shipment status.
13. `POST /api/agent/chat` — LangGraph-powered conversational AI customer service.
14. `POST /api/agent/logistics/check-and-ticket` — Logistics anomaly check and ticket generation.
15. `POST /api/agent/claim/submit` — Submit a warranty claim with RAG-assisted analysis.
16. `GET /api/seller/pending-claims` — List claims awaiting seller decision.
17. `POST /api/seller/claims/:id/approve` — Approve warranty claim (seller authorization).
18. `POST /api/seller/claims/:id/reject` — Reject warranty claim (seller authorization).
19. `GET /api/seller/crm-tags` — List CRM tags defined by the seller.
20. `POST /api/seller/crm-tags` — Create a new CRM tag.
21. `POST /api/seller/customers/:customer_id/tags/:tag_id` — Assign CRM tag to a customer.

---

## 7. Output Contract

When execution is complete, the Software Architect Agent produces a structured state update containing the 4 owned top-level keys:

```json
{
  "architecture": {
    "system_pattern": "layered",
    "components": [
      {
        "name": "Frontend",
        "responsibility": "React SPA delivering responsive storefront, fast-link checkout, and seller portals.",
        "dependencies": ["Backend API"],
        "interfaces": ["REST API", "HTTP"],
        "notes": "Consumes JSON endpoints from /api."
      },
      {
        "name": "Backend",
        "responsibility": "FastAPI service orchestrating business rules, stock consistency, and authentication.",
        "dependencies": ["Database", "Redis", "RAG Service"],
        "interfaces": ["FastAPI Routers", "SQLAlchemy ORM"],
        "notes": "Enforces atomic stock decrements and payment state machines."
      },
      {
        "name": "Database",
        "responsibility": "PostgreSQL relational persistence for ACID guarantees.",
        "dependencies": [],
        "interfaces": ["SQLAlchemy", "PostgreSQL Dialect"],
        "notes": "Handles migrations via Alembic."
      },
      {
        "name": "RAG Service",
        "responsibility": "ChromaDB vector retrieval and LangGraph orchestration for claims and chat.",
        "dependencies": ["Gemini LLM", "ChromaDB"],
        "interfaces": ["Python Service Calls"],
        "notes": "Advisory recommendations for seller approval."
      }
    ],
    "cross_cutting_concerns": [
      "Authentication and RBAC using JWT and Bcrypt",
      "Transactional integrity and atomic stock decrement",
      "Audit logs for payments, stock changes, and warranty claims",
      "Centralized error handling and RFC 7807 error envelopes"
    ],
    "design_details": {
      "stock_management": "PostgreSQL transactional conditional atomic decrements ensure that variant stock is decremented only upon payment verification. If stock is insufficient, the order is flagged.",
      "payment_verification": "Payment slip upload transitions payment to uploaded. Subsequent processing moves it to verified or rejected.",
      "checkout": "Fast-link sessions generate expiring tokens. Fast-link checkout sessions do not reserve inventory in advance.",
      "crm": "Sellers manage customer relationships by attaching CRMTag and UserCRMTag records to buyers.",
      "logistics": "Tracking anomaly detection identifies carrier shipment delays and creates a SupportTicket.",
      "warranty_rag": "Warranty claims leverage ChromaDB embeddings and Gemini via LangGraph; seller retains final approval.",
      "customer_service": "Customer support uses LangGraph and LangChain for intent analysis and escalations."
    },
    "notes": "Architectural baseline established for multi-agent fashion marketplace."
  },
  "technology_stack": {
    "frontend": {
      "technology": "React, TypeScript, Vite, Tailwind CSS, React Router",
      "status": "confirmed",
      "reason": "Modern, performant client-side SPA with type safety and responsive utility styling."
    },
    "backend": {
      "technology": "Python, FastAPI",
      "status": "confirmed",
      "reason": "High-performance asynchronous Python REST API with automatic OpenAPI documentation."
    },
    "database": {
      "technology": "PostgreSQL, SQLAlchemy, Alembic",
      "status": "confirmed",
      "reason": "ACID compliance for orders and inventory, robust ORM, and reliable schema migrations."
    },
    "ai": {
      "technology": "LangGraph, LangChain, Gemini",
      "status": "confirmed",
      "reason": "Stateful agentic workflows, conversational intent management, and multimodal policy evaluation."
    },
    "testing": {
      "technology": "Pytest",
      "status": "confirmed",
      "reason": "Comprehensive unit, integration, and contract test automation."
    },
    "integration": {
      "technology": "HTTP service boundaries and shared ProjectState",
      "status": "confirmed",
      "reason": "Standardized REST contracts and immutable cross-agent state dictionary."
    },
    "cache_queue": {
      "technology": "Redis, BullMQ",
      "status": "confirmed",
      "reason": "High-throughput ephemeral session caching and resilient background task processing."
    },
    "rag": {
      "technology": "ChromaDB",
      "status": "confirmed",
      "reason": "Fast local/embedded vector database for warranty policy embeddings and retrieval."
    },
    "authentication": {
      "technology": "JWT, Bcrypt",
      "status": "confirmed",
      "reason": "Stateless token-based authorization with industry-standard password hashing."
    },
    "api": {
      "technology": "REST, JSON",
      "status": "confirmed",
      "reason": "Standardized predictable communication contracts between frontend and backend."
    }
  },
  "database_schema": {
    "entities": [
      {
        "name": "User",
        "purpose": "Manages user identities, authentication credentials, and system roles.",
        "fields": [
          {"name": "id", "type": "INTEGER", "role": "primary_key"},
          {"name": "email", "type": "VARCHAR(255)", "role": "attribute"},
          {"name": "password_hash", "type": "VARCHAR(255)", "role": "attribute"},
          {"name": "role", "type": "VARCHAR(50)", "role": "attribute"},
          {"name": "created_at", "type": "TIMESTAMP", "role": "audit"}
        ],
        "relationships": ["One-to-many with Order", "One-to-many with UserCRMTag"],
        "design_notes": "Indexed on email for fast credential lookups."
      }
    ],
    "notes": "Relational schema designed for PostgreSQL with strict foreign keys and audit timestamps."
  },
  "api_specification": {
    "base_path": "/api",
    "style": "REST",
    "format": "JSON",
    "endpoints": [
      {
        "method": "POST",
        "path": "/api/auth/login",
        "purpose": "Authenticate user credentials and return JWT bearer token.",
        "authentication": "none",
        "request_summary": "{ email, password }",
        "response_summary": "{ access_token, token_type, user }",
        "api_design_notes": "Rate-limited to prevent brute force attempts.",
        "related_components": ["Backend", "Frontend"]
      }
    ]
  }
}
```

---

## 8. Validation & Error Handling

### 8.1 Validation Checklist for Generated Architecture:
Before delivering the output to `ProjectState`, verify:
1. **Top-Level Keys:** `architecture`, `technology_stack`, `database_schema`, and `api_specification` are all present.
2. **Architecture Components:** `system_pattern` is a non-empty string. `components` has at least 1 component with `name`, `responsibility`, `dependencies`, `interfaces`, and `notes`. `cross_cutting_concerns` is a non-empty list of strings.
3. **Design Details Invariants:** All 7 keys (`stock_management`, `payment_verification`, `checkout`, `crm`, `logistics`, `warranty_rag`, `customer_service`) are present, and each contains its mandatory keyword set (Section 6.1).
4. **Technology Stack:** Exactly the 10 defined categories are present. Every entry has `technology`, `status: "confirmed"`, and `reason`.
5. **Database Schema:** Contains `notes` and `entities`. `entities` includes at least the 14 mandatory entity models. Every entity has non-empty `name`, `purpose`, `design_notes`, valid `fields` list (each field having non-empty `name`, `type`, `role`), and valid `relationships` string list.
6. **API Specification:** `base_path` is `"/api"`, `style` is `"REST"`, `format` is `"JSON"`, and `endpoints` contains at least the 21 required routes with all required fields (`method`, `path`, `purpose`, `authentication`, `request_summary`, `response_summary`, `api_design_notes`, and `related_components` list).

### 8.2 Error Recovery & Repair Protocol:
- If an automated validator, test suite, or user provides `validation_feedback`, analyze the exact validation message.
- Re-inspect the draft against the missing entity, missing keyword, or structural invalidity.
- Correct the specific discrepancy while preserving all valid architectural details.
- Avoid repeating invalid payloads.

---

## 9. Handoff

The Software Architect Agent completes its role by returning the updated `ProjectState` with all 4 architectural fields populated.

### Handoff Protocol:
- **Receiver:** The Master Workflow Orchestrator (`.agents/skills/master-workflow/SKILL.md` or Antigravity Markdown Workflow controller).
- **Downstream Consumers:**
  - **Frontend Developer Agent:** Consumes `api_specification`, `technology_stack["frontend"]`, and `architecture["components"]` to implement UI pages, routing, and API integration.
  - **Backend Developer Agent:** Consumes `database_schema`, `api_specification`, `technology_stack["backend"]`, and `architecture["design_details"]` to implement FastAPI routers, SQLAlchemy models, and business logic.
- **Immediate Handoff Rule:** Once architectural deliverables (`architecture`, `technology_stack`, `database_schema`, `api_specification`) are complete, hand off immediately to Frontend and Backend Developer Agents without a mandatory intermediate human architecture approval pause.
- **Exception Blocker Protocol:** If critical information is missing or an unresolvable contradiction is identified that prevents sound design, report a structured `BLOCKER` and halt for human clarification. This exception must never be used to justify routine approval pauses.
- **Agent Boundary:** The Architect Agent **never** invokes the Frontend or Backend agents directly. Selecting and scheduling the next agent is exclusively the Master Workflow Orchestrator's responsibility.

---

## 10. Prohibited Actions

To maintain architectural integrity and agent boundaries, the Software Architect Agent is strictly forbidden from:

1. **Writing Application Source Code:**
   - Do NOT write or create React `.tsx`/`.jsx` components, CSS stylesheets, or HTML pages.
   - Do NOT write or create FastAPI router files, Python service implementations, or SQL migration scripts.
2. **Mutating Approved Business Requirements:**
   - Do NOT alter, remove, or silently overwrite PM requirements, user stories, or MVP scopes in `ProjectState`.
   - If a technical limitation conflicts with a requirement, flag the issue in `architecture["notes"]` or trigger a revision cycle via the PM Agent.
3. **Inventing Unsupported Technical Decisions:**
   - Do NOT replace PostgreSQL with MongoDB, change FastAPI to Django, or switch React to Vue without explicit user instruction and contract approval.
   - Do NOT invent unauthorized external APIs (e.g., live bank payment webhooks) that violate established project constraints.
4. **Violating Domain Invariants:**
   - Do NOT allow speculative stock deduction prior to payment verification.
   - Do NOT treat uploaded payment slips as verified payments.
   - Do NOT grant autonomous AI decision-making for warranty claims without human seller approval.
5. **Mutating Unowned State Fields:**
   - Do NOT modify `frontend_code`, `backend_code`, `test_cases`, `bugs`, or `security_findings`.

---

## 11. Completion Checklist

Before reporting completion of an architectural task, review every item:

- [ ] Input state has been verified to contain valid PM outputs (`project_goal`, `project_description`, `requirements`, `user_stories`, `mvp_scope`).
- [ ] Existing codebase contracts (`docs/agent_contract.md`, `docs/data_schema.md`) have been inspected and respected.
- [ ] `architecture` contains `system_pattern`, modular `components`, `cross_cutting_concerns`, and all 7 mandatory `design_details`.
- [ ] All 7 `design_details` sections contain their respective required architectural keywords.
- [ ] `technology_stack` contains all 10 confirmed categories with valid technical justifications.
- [ ] `database_schema` contains all 14 required entities with valid fields (`name`, `type`, `role`) and explicit relationships.
- [ ] Variant-level stock authority and payment slip verification states are clearly documented.
- [ ] `api_specification` includes `base_path: "/api"`, `style: "REST"`, `format: "JSON"`, and all 21 mandatory endpoints.
- [ ] No application code (React/FastAPI/SQL) was generated.
- [ ] No unowned `ProjectState` fields were modified or corrupted.
- [ ] Output is cleanly structured and ready for consumption by downstream Frontend and Backend Developer Agents via the Master Workflow Orchestrator.
