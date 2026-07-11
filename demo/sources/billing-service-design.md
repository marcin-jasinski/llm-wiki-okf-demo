# Billing service — design overview

Owner: Payments team. Status: production.

The Billing service is responsible for charging customers and issuing
invoices. When a checkout is confirmed, Billing authorizes and captures the
payment, records the charge, and emits an `invoice.created` event.

## Responsibilities

- Authorize and capture payments for confirmed carts.
- Issue invoices and store them for 7 years (finance requirement).
- Expose `POST /charges` (synchronous authorize+capture) and
  `GET /invoices/{id}`.

## Dependencies

- **PayRail** — our third-party payment gateway. Billing calls PayRail to move
  money; if PayRail is degraded, charges queue and retry with backoff.
- **Ledger service** — the source of truth for customer account balances and
  credit. Billing reads available credit from Ledger before authorizing and
  writes the settled amount back after capture. A Billing charge cannot
  complete while Ledger is unavailable.

## Callers

The Checkout service calls `POST /charges` synchronously during the final step
of an order. No other service calls Billing directly.

## On call

Billing pages the **Payments on-call** rotation. Sev1 if charge success rate
drops below 95% over 5 minutes.
