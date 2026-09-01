# MilestoneDeliveryClaim settlement paths

Contract: 0xdD44E5d445259009b8113482E5131479C00B5315
Transfers: emit_transfer

Path A — delivered + remainder
1. client fund()
2. resolve() -> delivered
3. pay_worker() pays payment_amount only
4. withdraw_remainder() returns leftover to client

Path B — not_delivered / unknown before deadline
1. resolve() may record verdict
2. refund_client() MUST fail until deadline_unix

Path C — refund after deadline
1. deadline_passed true
2. refund_client() returns remaining escrow
