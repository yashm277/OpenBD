# SRM — Software Requirements & Roadmap

## Purpose
This document captures the high-level software requirements, scope, stakeholders, milestones, and acceptance criteria for the Rise Counselors project.

## Scope
- Core user flows: counselor signup, client booking, session management
- Admin flows: user management, reporting, basic analytics
- Integrations: calendar sync, email notifications, payments (TBD)

## Stakeholders
- Product Owner: TBD
- Engineering Lead: TBD
- Designers: TBD
- QA: TBD

## Goals
1. Provide a reliable booking experience for clients and counselors.
2. Support secure user authentication and authorization.
3. Offer an admin dashboard for managing counselors and sessions.

## High-level Features
- User authentication (signup/login, password reset)
- Counselor profile management
- Client booking flow with availability calendar
- Session reminders (email / SMS)
- Payment integration (optional / milestone 2)
- Admin reporting dashboard

## Non-functional Requirements
- Security: user data encrypted in transit; follow OWASP basics
- Performance: pages should load within 2s on typical connections
- Scalability: design to allow horizontal scaling of backend services

## Milestones & Timeline (provisional)
- M1 — Project scaffolding, auth, basic models (2 weeks)
- M2 — Booking flow, calendar sync, notifications (3–4 weeks)
- M3 — Admin dashboard, reporting, payments (3 weeks)

## Acceptance Criteria (example)
- A client can register, view counselor availability, and book a session.
- A counselor can set availability and view bookings on their calendar.
- Admin can list users and export a CSV of sessions.

## Open Questions / Risks
- Which payment provider to use (Stripe, PayPal, other)?
- Required privacy/compliance constraints (HIPAA, GDPR?)
- Hosting and deployment preferences

## Next Steps
1. Create initial repo scaffold (package.json / pyproject / README).
2. Choose stack (Node/Express + React or Django + React) and add dev scripts.
3. Implement M1 features and run CI.

---
_Created on 2026-02-13_
