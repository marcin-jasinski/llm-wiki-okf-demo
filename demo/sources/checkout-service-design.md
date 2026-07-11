# Checkout service — design overview

Owner: Storefront team. Status: production.

Checkout turns a shopping cart into a placed order. It validates the cart,
reserves inventory, and then takes payment by calling the Billing service.

## Flow

1. Validate the cart and price it.
2. Reserve inventory for the line items.
3. Call Billing `POST /charges` **synchronously** to authorize and capture
   payment.
4. On a successful charge, create the order and return a confirmation.

## Failure behavior

Checkout **fails closed**: if the Billing call errors or times out, Checkout
releases the inventory reservation and returns an error to the shopper — no
order is created and no money is taken. This means a Billing outage stops all
new orders across the storefront, even though carts and browsing still work.

## Dependencies

- **Billing service** — synchronous, on the critical path. This is the only
  hard runtime dependency of Checkout.
- Inventory service — for reservations (soft; degrades to "backorder" mode).

## On call

Checkout pages the **Storefront on-call** rotation. When the cause is a
downstream Billing failure, Storefront on-call escalates to Payments on-call
(see the checkout outage runbook).
