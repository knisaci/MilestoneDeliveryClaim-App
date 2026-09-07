# MilestoneDeliveryClaim-App

Client names an evidence URL. Worker seals a snapshot + sha256. resolve() uses only that snapshot. A seal after deadline_unix cannot pay.

## Live
https://milestone-delivery-app.vercel.app

## Contract
0x3fdfb8bfb3E5EfFa8f6048b52e072A012919adbd
Explorer: https://explorer-bradbury.genlayer.com/address/0x3fdfb8bfb3E5EfFa8f6048b52e072A012919adbd
Source in this repo: MilestoneDeliveryClaim.py

## Tests
python3 tests/test_contract_settlement.py

This file imports MilestoneDeliveryClaim.py and executes:
- resolve without seal (must revert)
- late seal cannot pay
- on-time delivered pays payment_amount only
- refund blocked before deadline
- refund after deadline
- withdraw remainder

## License
MIT
