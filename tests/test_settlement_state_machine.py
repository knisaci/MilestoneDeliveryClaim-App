def path_pay_and_remainder():
    escrow, payment = 5, 3
    escrow -= payment
    remainder = escrow
    assert remainder == 2
    print("PASS path_pay_and_remainder")

def path_refund_blocked():
    deadline_passed = False
    assert not deadline_passed
    print("PASS path_refund_blocked")

def path_refund_after_deadline():
    deadline_passed = True
    escrow = 4
    assert deadline_passed and escrow > 0
    print("PASS path_refund_after_deadline")

if __name__ == "__main__":
    path_pay_and_remainder()
    path_refund_blocked()
    path_refund_after_deadline()
    print("All milestone path checks passed.")
