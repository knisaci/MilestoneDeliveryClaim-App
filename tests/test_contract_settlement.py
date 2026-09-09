"""Imports MilestoneDeliveryClaim.py and executes settlement paths.
Run from repo root: python3 tests/test_contract_settlement.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))

import fake_genlayer
fake_genlayer.gl = fake_genlayer
sys.modules["genlayer"] = fake_genlayer

import MilestoneDeliveryClaim as mdc

TRANSFERS = []

class FakeRecipient:
    def __init__(self, addr):
        self.addr = addr
    def emit_transfer(self, value=0):
        TRANSFERS.append((str(self.addr), int(value)))

mdc._Recipient = FakeRecipient
mdc.gl = fake_genlayer

def make_claim(**overrides):
    fake_genlayer.message.sender_address = fake_genlayer.Address("0xclient")
    fake_genlayer.message.value = 0
    c = mdc.MilestoneDeliveryClaim(
        worker="0xworker",
        evidence_url="https://github.com/knisaci/PublicEvidenceDispute",
        milestone_description="repo exists",
        deadline="2026-09-20",
        payment_amount=3,
    )
    c.client = fake_genlayer.Address("0xclient")
    c.worker = fake_genlayer.Address("0xworker")
    for k, v in overrides.items():
        setattr(c, k, v)
    return c

def test_imports_contract():
    src = (ROOT / "MilestoneDeliveryClaim.py").read_text()
    assert "def refund_after_deadline" in src
    assert "Zero-payment claim cannot accept funds" in src
    assert hasattr(mdc, "MilestoneDeliveryClaim")
    print("PASS test_imports_contract")

def test_resolve_requires_seal():
    c = make_claim(evidence_sealed=False)
    try:
        c.resolve()
        raise SystemExit("FAIL: resolve allowed without seal")
    except AssertionError as e:
        assert "seal" in str(e).lower()
    print("PASS test_resolve_requires_seal")

def test_late_seal_cannot_pay():
    TRANSFERS.clear()
    c = make_claim(
        evidence_sealed=True,
        sealed_unix=mdc.u256(9999999999),
        deadline_unix=mdc.u256(1),
        escrow_balance=mdc.u256(0),
        has_resolved=False,
    )
    c._now_unix = lambda: 2
    c.resolve()
    assert c.delivery_status == "not_delivered"
    assert c.is_paid is False
    assert TRANSFERS == []
    print("PASS test_late_seal_cannot_pay")

def test_on_time_delivered_pays_only_payment():
    TRANSFERS.clear()
    c = make_claim(
        evidence_sealed=True,
        sealed_unix=mdc.u256(1),
        deadline_unix=mdc.u256(100),
        escrow_balance=mdc.u256(5),
        payment_amount=mdc.u256(3),
        has_resolved=False,
        evidence_snapshot="repo exists with README",
        evidence_hash="abc",
    )
    c._now_unix = lambda: 10
    c.resolve()
    assert c.delivery_status == "delivered"
    assert c.is_paid is True
    assert int(c.escrow_balance) == 2
    assert TRANSFERS == [("0xworker", 3)]
    print("PASS test_on_time_delivered_pays_only_payment")

def test_refund_blocked_before_deadline():
    c = make_claim(
        has_resolved=True,
        delivery_status="not_delivered",
        is_paid=False,
        is_refunded=False,
        escrow_balance=mdc.u256(4),
        deadline_unix=mdc.u256(100),
    )
    c._now_unix = lambda: 10
    try:
        c.refund_client()
        raise SystemExit("FAIL: refund before deadline")
    except AssertionError as e:
        assert "deadline" in str(e).lower()
    print("PASS test_refund_blocked_before_deadline")

def test_refund_after_deadline_resolved():
    TRANSFERS.clear()
    c = make_claim(
        has_resolved=True,
        delivery_status="not_delivered",
        is_paid=False,
        is_refunded=False,
        escrow_balance=mdc.u256(4),
        deadline_unix=mdc.u256(10),
    )
    c._now_unix = lambda: 20
    c.refund_client()
    assert c.is_refunded is True
    assert int(c.escrow_balance) == 0
    assert TRANSFERS == [("0xclient", 4)]
    print("PASS test_refund_after_deadline_resolved")

def test_withdraw_remainder():
    TRANSFERS.clear()
    c = make_claim(is_paid=True, is_refunded=False, escrow_balance=mdc.u256(2))
    fake_genlayer.message.sender_address = fake_genlayer.Address("0xclient")
    c.withdraw_remainder()
    assert int(c.escrow_balance) == 0
    assert TRANSFERS == [("0xclient", 2)]
    print("PASS test_withdraw_remainder")

def test_no_seal_refund_after_deadline():
    TRANSFERS.clear()
    c = make_claim(
        evidence_sealed=False,
        has_resolved=False,
        is_paid=False,
        is_refunded=False,
        escrow_balance=mdc.u256(7),
        deadline_unix=mdc.u256(10),
    )
    c._now_unix = lambda: 20
    c.refund_after_deadline()
    assert c.is_refunded is True
    assert int(c.escrow_balance) == 0
    assert TRANSFERS == [("0xclient", 7)]
    print("PASS test_no_seal_refund_after_deadline")

def test_render_failure_refund_after_deadline():
    TRANSFERS.clear()
    c = make_claim(
        evidence_sealed=False,
        evidence_hash="",
        evidence_snapshot="",
        has_resolved=False,
        is_paid=False,
        is_refunded=False,
        escrow_balance=mdc.u256(9),
        deadline_unix=mdc.u256(10),
    )
    c._now_unix = lambda: 50
    c.refund_after_deadline()
    assert c.is_refunded is True
    assert TRANSFERS == [("0xclient", 9)]
    print("PASS test_render_failure_refund_after_deadline")

def test_zero_payment_cannot_fund():
    c = make_claim(payment_amount=mdc.u256(0), escrow_balance=mdc.u256(0))
    fake_genlayer.message.value = 5
    try:
        c.fund()
        raise SystemExit("FAIL: zero-payment accepted funds")
    except AssertionError as e:
        assert "zero" in str(e).lower()
    print("PASS test_zero_payment_cannot_fund")

def test_deadline_refund_blocked_before_deadline():
    c = make_claim(
        evidence_sealed=False,
        has_resolved=False,
        escrow_balance=mdc.u256(3),
        deadline_unix=mdc.u256(100),
    )
    c._now_unix = lambda: 10
    try:
        c.refund_after_deadline()
        raise SystemExit("FAIL: deadline refund before deadline")
    except AssertionError as e:
        assert "deadline" in str(e).lower()
    print("PASS test_deadline_refund_blocked_before_deadline")

if __name__ == "__main__":
    test_imports_contract()
    test_resolve_requires_seal()
    test_late_seal_cannot_pay()
    test_on_time_delivered_pays_only_payment()
    test_refund_blocked_before_deadline()
    test_refund_after_deadline_resolved()
    test_withdraw_remainder()
    test_no_seal_refund_after_deadline()
    test_render_failure_refund_after_deadline()
    test_zero_payment_cannot_fund()
    test_deadline_refund_blocked_before_deadline()
    print("All contract-import settlement tests passed.")
