# MilestoneDeliveryClaim-App

Sealed milestone escrow on Testnet Bradbury.

Worker seals a snapshot + hash. resolve() uses only that snapshot. A late seal cannot pay.
After deadline_unix, refund_after_deadline() returns remaining escrow to the client even if nothing was sealed and even if page render failed.
fund() rejects payment_amount == 0.

## Live
https://milestone-delivery-app.vercel.app

## Contract
0xc06Ea3fb95809E4741b28d6BF2763A335Ae1c4d5
Explorer: https://explorer-bradbury.genlayer.com/address/0xc06Ea3fb95809E4741b28d6BF2763A335Ae1c4d5
Source in this repo: MilestoneDeliveryClaim.py

## Tests
python3 tests/test_contract_settlement.py

Imports MilestoneDeliveryClaim.py and executes:
- resolve without seal (revert)
- late seal cannot pay
- on-time delivered pays payment_amount only
- refund_client blocked before deadline
- no-seal refund_after_deadline
- render-failure (never sealed) refund_after_deadline
- zero-payment fund() reverts
- withdraw remainder

## License
MIT
