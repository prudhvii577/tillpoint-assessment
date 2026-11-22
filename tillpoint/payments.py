
"""Payment provider webhooks. The provider retries a delivery until it gets a 2xx, so events can repeat."""
from . import db


class PaymentError(Exception):
    pass


class Payments:
    def __init__(self, conn):
        self.conn = conn

    def handle_event(self, event, now=None):
        """Record successful payments and identify orders that receive excess payment."""
        if event.get("type") != "payment.succeeded":
            return None

        order = self.conn.execute(
            "SELECT * FROM orders WHERE id = ?",
            (event["order_id"],)
        ).fetchone()

        if order is None:
            raise PaymentError(f"payment for unknown order {event['order_id']}")

        if order["status"] == "cancelled":
            raise PaymentError(f"order {order['id']} is cancelled")

        cursor = self.conn.execute(
            """
            INSERT OR IGNORE INTO payments
            (order_id, event_id, amount_cents, received_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                order["id"],
                event["id"],
                event["amount_cents"],
                db.to_iso(now or db.utcnow()),
            ),
        )

        # Ignore repeated delivery of the same provider event.
        if cursor.rowcount == 0:
            return order["status"]

        total_paid = self.paid_cents(order["id"])
        total_due = order["total_cents"]

        if total_paid > total_due:
            new_status = "overpaid"
        elif total_paid >= total_due and order["status"] == "pending":
            new_status = "paid"
        else:
            return order["status"]

        self.conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (new_status, order["id"])
        )

        return new_status

    def paid_cents(self, order_id):
        row = self.conn.execute(
            """
            SELECT COALESCE(SUM(amount_cents), 0) AS paid
            FROM payments WHERE order_id = ?
            """,
            (order_id,)
        ).fetchone()

        return row["paid"]
