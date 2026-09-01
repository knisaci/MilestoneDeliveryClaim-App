# MilestoneDeliveryClaim-App

Full GenLayer Project: milestone delivery verified from a public evidence URL.

## Live
https://milestone-delivery-app.vercel.app

## Contract
0xdD44E5d445259009b8113482E5131479C00B5315
Explorer: https://explorer-bradbury.genlayer.com/address/0xdD44E5d445259009b8113482E5131479C00B5315
Source in this repo: MilestoneDeliveryClaim.py

## Safeguards
- Refund of not_delivered / unknown is blocked until deadline_unix (contract-side time check)
- Worker payout is payment_amount only
- Leftover escrow is recoverable via withdraw_remainder
- emit_transfer for all payouts
- AI decision rules live in the same source as Explorer

## Tests
python3 tests/test_settlement_state_machine.py

## License
MIT
