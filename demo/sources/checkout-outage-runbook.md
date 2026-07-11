# Runbook: checkout returning 5xx errors

Use this when checkout error rate is elevated or shoppers report "something
went wrong at payment".

## Symptoms

- Elevated 5xx on `POST /orders`.
- Drop in completed orders while cart/browse traffic is normal.

## Triage

1. **Check Billing health first.** Most checkout outages are a downstream
   Billing failure — Checkout calls Billing synchronously and fails closed, so
   a Billing problem surfaces as checkout errors. Look at the Billing charge
   success rate dashboard.
2. **Check PayRail status.** If Billing is failing to capture, open the PayRail
   status page — a gateway incident makes charges queue and time out.
3. **Check Ledger lag.** Billing reads available credit from the Ledger service
   before authorizing. If Ledger is slow or down, charges stall. Check Ledger
   connection-pool saturation.

## Escalation

If the root cause is Billing, PayRail, or Ledger, page **Payments on-call** and
hand off — Storefront on-call owns the symptom, Payments on-call owns the fix.
Declare a Sev1 if new orders are fully stopped.
