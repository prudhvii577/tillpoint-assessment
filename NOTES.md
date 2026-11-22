# NOTES

## 1. Report

> Finance says that on some days the revenue in the daily report is higher than what the payment provider paid out, and a few orders show more money received than their total.

**Status:** fixed

**What I saw:** The same payment webhook could be processed more than once. Each delivery inserted another payment record, increasing the amount received for the order and the daily revenue.

**Root cause:** The payment handler did not prevent duplicate processing of the same provider event.

**Fix and why:** Added a unique index on `payments.event_id` and changed the payment insertion to `INSERT OR IGNORE`. The order status is updated only when a new payment record is inserted. This prevents repeated delivery of the same event from being counted more than once.

**How I verified it:** Added `test_duplicate_webhook_does_not_duplicate_payment`. The test failed before the fix because the received amount became 2400 instead of 1200. It passed after the fix. The complete test suite also passed.

**Commits:** `44d437c`

## 2. Report

> Products show as sold out, or nearly, while the shelf is full. Staff say it gets worse on days when many customers abandon checkout.

**Status:** fixed

**What I saw:** Stock was reserved when an order was created. When a pending order was cancelled, the reserved stock was not restored.

**Root cause:** The cancellation logic restored stock for paid orders but did not handle pending orders.

**Fix and why:** Updated the cancellation logic to restore stock for both pending and paid orders. The stock release and order status update are performed inside a transaction so that the changes remain consistent.

**How I verified it:** Added `test_cancel_pending_order_restores_stock`. Before the fix, the stock remained at 1 instead of returning to 3. The test passed after the fix. The complete test suite also passed.

**Commits:** `c592b88`

## 3. Report

> Customers in taxed regions who used a coupon say the tax on their receipt is too high. Receipts without a coupon are right.

**Status:** fixed

**What I saw:** Tax was calculated using the original subtotal even when a coupon discount was applied.

**Root cause:** The discount was calculated, but the tax calculation still used the subtotal before discount.

**Fix and why:** Changed the pricing calculation to subtract the coupon discount from the subtotal before calculating tax. This ensures that tax is calculated on the discounted amount.

**How I verified it:** Added `test_coupon_discount_is_applied_before_tax`. Before the fix, the actual tax was 87 cents instead of the expected 78 cents. The test passed after the fix. The complete test suite also passed.

**Commits:** `cd526ba`

## 4. Report

> Our shop in India (UTC+5:30) says sales taken in the morning do not appear in that day's report and turn up under the day before.

**Status:** fixed

**What I saw:** The daily report used an incorrect UTC boundary when converting the local date into UTC.

**Root cause:** The UTC offset was added instead of being subtracted when calculating the UTC start of the local day.

**Fix and why:** Updated `day_bounds_utc()` to subtract the UTC offset from the local day start. This correctly converts the local reporting period into UTC.

**How I verified it:** Added `test_daily_sales_uses_india_timezone` using a payment at 20:00 UTC, which falls on the next calendar day in India. Before the fix, the report returned zero revenue and zero orders. After the fix, it returned 1200 cents and one order. The complete test suite also passed.

**Commits:** `81c436a`

## 5. Report

> Ever since we started running two server workers, we have sold more units of an item than we had, and its stock went negative.

**Status:** fixed

**What I saw:** The stock reservation logic relied on cached stock information and performed the stock check separately from the update. This could allow a reservation based on outdated stock.

**Root cause:** The stock check and stock deduction were not performed as one atomic database operation.

**Fix and why:** Changed the reservation logic to use a conditional SQL update that decreases stock only when the available quantity is sufficient. Also invalidated the cached stock value after the update. This makes the database enforce the stock limit during reservation.

**How I verified it:** Added `test_concurrent_stock_change_does_not_allow_negative_stock`. The test preloads the stock cache, changes the database stock to zero to simulate another worker updating it, and verifies that the reservation raises `OutOfStock` instead of allowing negative stock. The test passed after the fix. The complete test suite also passed.

**Commits:** `413e553`

## 6. Open question

> Sometimes a customer really does pay twice for one order (two separate payments, not a retry of the same one).

**My decision:** Keep both genuine payment records and mark the order as `overpaid` when the total amount received exceeds the order total.

**Why:** A repeated delivery of the same payment event should not create another payment record. However, two different successful payment events represent two actual payments and should both be recorded. Marking the order as overpaid makes the situation visible without losing payment history.

**What it costs:** The system does not automatically refund the extra payment. Someone must review the overpaid order and arrange a refund or reconciliation manually. The payment records remain in the database for audit purposes.

**What I built:** Updated payment handling to calculate the total amount received for an order. If the amount exceeds the order total, the order status changes to `overpaid`. Also updated cancellation to restore reserved stock when an overpaid order is cancelled. No automatic refund functionality was added.

**How I verified it:** Added `test_separate_second_payment_marks_order_overpaid` to verify that two distinct successful payment events are recorded and the order becomes overpaid. Added `test_cancel_overpaid_order_restores_stock` to verify that cancelling an overpaid order restores stock. Both tests passed. The complete test suite passed with 14 tests.

**Commits:** `ea1c56e`

## Other things I noticed

No additional issues were identified during the work on the six reported problems. I did not make changes outside the scope of these reports.

## Session logs

AI tool used: ChatGPT.

- `session_logs/README.md` — describes the AI session log files.
- `session_logs/chatgpt_session.md` — complete ChatGPT conversation log for this assessment.

