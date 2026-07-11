# On-call policy

Meridian runs three on-call rotations. Every production service maps to exactly
one rotation that owns its pages.

## Rotations

- **Payments on-call** — owns the Billing service and the Ledger service.
  Also the escalation target for any payment-capture problem, including PayRail
  gateway incidents.
- **Storefront on-call** — owns the Checkout service and the Inventory service.
- **Platform on-call** — owns shared infrastructure (databases, networking,
  the message bus).

## Severity levels

- **Sev1** — customer-facing revenue impact (e.g. new orders fully stopped).
  Page immediately, declare an incident, notify the incident channel.
- **Sev2** — degraded but working (e.g. elevated latency, partial failures).
- **Sev3** — no customer impact; handle next business day.

## Escalation rule

The rotation that owns the *symptom* takes the first page. If triage shows the
root cause belongs to another service, hand off to that service's rotation.
Storefront-to-Payments handoffs during checkout outages are the common case.
