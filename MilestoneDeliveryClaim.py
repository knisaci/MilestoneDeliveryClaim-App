# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from datetime import datetime, timezone
import json
import hashlib


@gl.evm.contract_interface
class _Recipient:
    class View:
        pass
    class Write:
        pass


class MilestoneDeliveryClaim(gl.Contract):
    client: Address
    worker: Address
    evidence_url: str
    milestone_description: str
    deadline: str
    deadline_unix: u256

    payment_amount: u256
    escrow_balance: u256

    evidence_snapshot: str
    evidence_hash: str
    evidence_sealed: bool
    sealed_unix: u256

    status: str
    has_resolved: bool
    is_paid: bool
    is_refunded: bool

    delivery_status: str
    note: str

    def __init__(self, worker: str, evidence_url: str, milestone_description: str, deadline: str, payment_amount: int):
        self.client = gl.message.sender_address
        self.worker = Address(worker)
        self.evidence_url = evidence_url
        self.milestone_description = milestone_description
        self.deadline = deadline
        self.deadline_unix = u256(self._deadline_to_unix(deadline))
        self.payment_amount = u256(payment_amount)
        self.escrow_balance = gl.message.value
        self.evidence_snapshot = ""
        self.evidence_hash = ""
        self.evidence_sealed = False
        self.sealed_unix = u256(0)
        self.status = "open"
        self.has_resolved = False
        self.is_paid = False
        self.is_refunded = False
        self.delivery_status = ""
        self.note = ""
        if self.escrow_balance >= self.payment_amount and self.payment_amount > u256(0):
            self.status = "funded"

    def _deadline_to_unix(self, deadline_str: str) -> int:
        y, m, d = [int(x) for x in deadline_str.strip().split("-")]
        return int(datetime(y, m, d, 23, 59, 59, tzinfo=timezone.utc).timestamp())

    def _now_unix(self) -> int:
        return int(datetime.now(timezone.utc).timestamp())

    def _deadline_passed(self) -> bool:
        return self._now_unix() >= int(self.deadline_unix)

    def _sealed_on_time(self) -> bool:
        return self.evidence_sealed and int(self.sealed_unix) <= int(self.deadline_unix)

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

    @gl.public.view
    def get_claim(self) -> dict:
        return {
            "client": str(self.client),
            "worker": str(self.worker),
            "evidence_url": self.evidence_url,
            "evidence_hash": self.evidence_hash,
            "evidence_sealed": self.evidence_sealed,
            "sealed_unix": int(self.sealed_unix),
            "sealed_on_time": self._sealed_on_time(),
            "milestone_description": self.milestone_description,
            "deadline": self.deadline,
            "deadline_unix": int(self.deadline_unix),
            "now_unix": self._now_unix(),
            "deadline_passed": self._deadline_passed(),
            "payment_amount": int(self.payment_amount),
            "escrow_balance": int(self.escrow_balance),
            "status": self.status,
            "has_resolved": self.has_resolved,
            "is_paid": self.is_paid,
            "is_refunded": self.is_refunded,
            "delivery_status": self.delivery_status,
            "note": self.note,
        }

    @gl.public.write.payable
    def fund(self) -> dict:
        require(not self.is_paid and not self.is_refunded, "Settled")
        amount = gl.message.value
        require(amount > u256(0), "Must send GEN")
        self.escrow_balance += amount
        if self.escrow_balance >= self.payment_amount and self.status == "open":
            self.status = "funded"
        return {"ok": True, "escrow_balance": int(self.escrow_balance)}

    @gl.public.write
    def seal_evidence(self) -> dict:
        require(gl.message.sender_address == self.worker, "Only worker")
        require(not self.has_resolved, "Already resolved")
        require(not self.evidence_sealed, "Already sealed")
        url = self.evidence_url

        def leader_fn() -> dict:
            page = gl.nondet.web.render(url, mode="text")
            text = str(page)[:8000]
            return {"snapshot": text, "hash": hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()}

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            leader = leader_result.calldata
            if not isinstance(leader, dict):
                return False
            mine = leader_fn()
            return mine.get("hash") == leader.get("hash")

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        self.evidence_snapshot = str(result.get("snapshot", ""))[:8000]
        self.evidence_hash = str(result.get("hash", ""))
        self.evidence_sealed = True
        self.sealed_unix = u256(self._now_unix())
        return {
            "ok": True,
            "evidence_hash": self.evidence_hash,
            "sealed_unix": int(self.sealed_unix),
            "sealed_on_time": self._sealed_on_time(),
        }

    def _pay_worker(self) -> dict:
        require(self.escrow_balance >= self.payment_amount, "Underfunded")
        _Recipient(self.worker).emit_transfer(value=self.payment_amount)
        self.escrow_balance -= self.payment_amount
        self.is_paid = True
        self.status = "paid"
        return {"ok": True, "status": "paid", "remainder": int(self.escrow_balance)}

    def _refund_client(self) -> dict:
        require(self._deadline_passed(), "Deadline not reached")
        require(self.escrow_balance > u256(0), "Nothing to refund")
        amount = self.escrow_balance
        _Recipient(self.client).emit_transfer(value=amount)
        self.escrow_balance = u256(0)
        self.is_refunded = True
        self.status = "refunded"
        return {"ok": True, "status": "refunded", "refunded": int(amount)}

    @gl.public.write
    def resolve(self) -> dict:
        require(self.payment_amount > u256(0), "Invalid payment")
        require(self.evidence_sealed, "Evidence not sealed")
        if self.has_resolved and self.status in ("paid", "refunded"):
            return {"ok": False, "message": "Already settled", "status": self.status}
        if self.has_resolved:
            if self.delivery_status == "delivered" and not self.is_paid:
                return self._pay_worker()
            if self.delivery_status in ("not_delivered", "unknown") and not self.is_refunded:
                return self._refund_client()
            return {"ok": False, "message": "Nothing to settle", "status": self.status}

        if not self._sealed_on_time():
            self.has_resolved = True
            self.delivery_status = "not_delivered"
            self.note = "Evidence sealed after deadline"
            self.status = "not_delivered"
            if self.escrow_balance > u256(0) and self._deadline_passed():
                return self._refund_client()
            return {"ok": True, "status": self.status, "note": self.note}

        snapshot = self.evidence_snapshot
        evidence_hash = self.evidence_hash
        milestone_description = self.milestone_description
        deadline = self.deadline

        def leader_fn() -> dict:
            prompt = f"""
Verify milestone delivery using ONLY the sealed snapshot. Do not use a live page.

Milestone: {milestone_description}
Deadline: {deadline}
Sealed snapshot hash: {evidence_hash}
Sealed snapshot: {snapshot[:6000]}

JSON only:
{{"delivery_status":"delivered"|"not_delivered"|"unknown","note":"<one sentence>"}}

Rules:
- delivered if the snapshot clearly shows the described work exists.
- not_delivered if the snapshot shows missing or incomplete work.
- unknown if insufficient.
- Do not invent facts.
"""
            raw = gl.nondet.exec_prompt(prompt, response_format="json")
            if not isinstance(raw, dict):
                raw = json.loads(str(raw).replace("```json", "").replace("```", "").strip())
            status = str(raw.get("delivery_status", "unknown")).lower().strip()
            if status not in ("delivered", "not_delivered", "unknown"):
                status = "unknown"
            return {"delivery_status": status, "note": str(raw.get("note", ""))[:300]}

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            leader = leader_result.calldata
            if not isinstance(leader, dict):
                return False
            mine = leader_fn()
            return mine["delivery_status"] == leader.get("delivery_status")

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        self.has_resolved = True
        self.delivery_status = str(result["delivery_status"])
        self.note = str(result.get("note", ""))[:300]
        self.status = self.delivery_status

        if self.delivery_status == "delivered":
            if self.escrow_balance >= self.payment_amount:
                return self._pay_worker()
            return {"ok": True, "status": "delivered", "message": "Underfunded. fund() then pay_worker()."}

        if self.escrow_balance > u256(0) and self._deadline_passed():
            return self._refund_client()
        return {"ok": True, "status": self.status, "note": self.note}

    @gl.public.write
    def pay_worker(self) -> dict:
        require(self.has_resolved, "Not resolved")
        require(self.delivery_status == "delivered", "Not delivered")
        require(not self.is_paid, "Already paid")
        require(not self.is_refunded, "Already refunded")
        return self._pay_worker()

    @gl.public.write
    def refund_client(self) -> dict:
        require(self.has_resolved, "Not resolved")
        require(self.delivery_status in ("not_delivered", "unknown"), "Not refundable")
        require(not self.is_refunded, "Already refunded")
        require(not self.is_paid, "Already paid")
        require(self._deadline_passed(), "Deadline not reached")
        return self._refund_client()

    @gl.public.write
    def withdraw_remainder(self) -> dict:
        require(gl.message.sender_address == self.client, "Only client")
        require(self.is_paid, "Worker not paid yet")
        require(not self.is_refunded, "Already refunded")
        require(self.escrow_balance > u256(0), "Nothing left")
        amount = self.escrow_balance
        _Recipient(self.client).emit_transfer(value=amount)
        self.escrow_balance = u256(0)
        return {"ok": True, "withdrawn": int(amount)}
