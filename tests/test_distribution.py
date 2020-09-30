import json
import random
import pytest
from brownie import Wei
from brownie.exceptions import VirtualMachineError


def test_merkle(distributor, tree, dai, ychad):
    dai.transfer(distributor, tree['tokenTotal'], {'from': ychad})
    assert dai.balanceOf(distributor) == tree['tokenTotal']

    account = random.choice(list(tree['claims']))
    claim = tree['claims'][account]
    tx = distributor.claim(claim['index'], account, claim['amount'], claim['proof'])
    tx.info()
    assert 'Claimed' in tx.events
    assert dai.balanceOf(account) == Wei(claim['amount'])

    with pytest.raises(VirtualMachineError):
        tx = distributor.claim(claim['index'], account, claim['amount'], claim['proof'])

    with pytest.raises(VirtualMachineError):
        tx = distributor.claim(123, ychad, '1000000 ether', claim['proof'])
