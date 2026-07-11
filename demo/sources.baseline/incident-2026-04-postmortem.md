# Postmortem: 2026-04-12 checkout outage

Severity: Sev1. Duration: 38 minutes. Author: Payments on-call.

## Summary

New orders were fully stopped for 38 minutes when the Ledger service exhausted
its database connection pool. Billing could not read account balances, so
charges timed out; Checkout fails closed, so every order attempt errored.

## Timeline

- 14:02 — Ledger connection-pool utilization hits 100% after a slow migration
  left idle transactions open.
- 14:05 — Billing charge success rate falls below 95%; Payments on-call paged.
- 14:06 — Storefront on-call paged for checkout 5xx; escalates to Payments per
  the checkout outage runbook.
- 14:20 — Idle Ledger transactions killed; pool recovers.
- 14:40 — Charge success rate back to normal; incident closed.

## Root cause

The Ledger service had no cap on transaction lifetime. A migration held
connections open, saturating the pool. Billing's dependency on Ledger turned a
Ledger-only problem into a full checkout outage.

## Action items

- Ledger: add an idle-transaction timeout and pool-saturation alerting.
- Billing: treat Ledger read failures as a fast, retryable error instead of
  blocking the whole charge.
- Docs: the Ledger service still has no design page of its own — write one.
