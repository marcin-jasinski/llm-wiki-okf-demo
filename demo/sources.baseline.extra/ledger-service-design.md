# Ledger service — design overview

Owner: Payments team. Status: production.

The Ledger service is the source of truth for customer account balances and
credit. Billing reads available credit from Ledger before authorizing a charge
and writes the settled amount back after capture.

## Responsibilities

- Track customer account balances and available credit.
- Expose `GET /accounts/{id}/balance` and `POST /accounts/{id}/settle`.
- Own the transactional record of every balance-affecting event.

## Callers

The Billing service calls Ledger synchronously on the critical path of every
charge — a balance check before authorizing, a settlement write after capture.
A Billing charge cannot complete while Ledger is unavailable (see the
2026-04-12 postmortem).

## Dependencies

- Its own Postgres database. No external service dependencies.

## Reliability

Following the 2026-04-12 postmortem — a migration left idle transactions open
and exhausted the connection pool — Ledger added an idle-transaction timeout
and pool-saturation alerting.

## On call

Ledger pages the **Payments on-call** rotation, the same rotation that owns
Billing.
