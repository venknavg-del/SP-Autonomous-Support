# Runbook: Null Pointer Exception in Checkout Service

## Symptoms
- High error rate on the `/api/checkout` endpoint.
- "NullPointerException" appearing in logs for `PaymentService.java`.
- Customers reporting failures during the final checkout step.

## Root Cause
Typically caused by missing guard clauses when processing empty wallets, invalid payment tokens, or null response objects from 3rd party payment gateways.

## Resolution Steps
1. **Immediate Mitigation:**
   - If a specific payment gateway is failing consistently and returning nulls, toggle the gateway feature flag off to force the fallback gateway: `feature-flags set use_primary_gateway false`
   - Review recent deployments for the `checkout-service`. If deployed within the last 2 hours, initiate a rollback.
2. **Investigation:**
   - Look for the exact line number in the stack trace. Commonly occurs when calling `.getBalance()` or `.getPaymentToken()` on a null user object.
3. **Code Fix Required:**
   - A code fix is usually required to add robust null checking. e.g. `if (user == null || user.getBalance() == null) { return BigDecimal.ZERO; }`
   - Escalate to the L3 Engineering team to draft and review the fix.
