class Address(str):
    pass

class u256(int):
    def __new__(cls, val=0):
        return int.__new__(cls, int(val))

def require(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

class _Write:
    def __call__(self, fn=None):
        if fn is None:
            return lambda f: f
        return fn
    def payable(self, fn):
        return fn

class _Public:
    def __init__(self):
        self.write = _Write()
    def view(self, fn):
        return fn

class _Message:
    sender_address = Address("0xclient")
    value = 0

class _VM:
    class Return:
        def __init__(self, calldata):
            self.calldata = calldata
    @staticmethod
    def run_nondet_unsafe(leader_fn, validator_fn):
        return leader_fn()

class _Nondet:
    class web:
        @staticmethod
        def render(url, mode="text"):
            return "sealed snapshot for " + url
    @staticmethod
    def exec_prompt(prompt, response_format="json"):
        return {"delivery_status": "delivered", "note": "ok"}

class _Evm:
    @staticmethod
    def contract_interface(cls):
        return cls

class Contract:
    pass

public = _Public()
message = _Message()
vm = _VM()
nondet = _Nondet()
evm = _Evm()
gl = None
