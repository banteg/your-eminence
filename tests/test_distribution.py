import random
import brownie
from brownie import Wei


def test_merkle(distributor, tree, dai, ychad):
    dai.transfer(distributor, tree['tokenTotal'], {'from': ychad})
    assert dai.balanceOf(distributor) == tree['tokenTotal']

    account = random.choice(list(tree['claims']))
    claim = tree['claims'][account]
    tx = distributor.claim(claim['index'], account, claim['amount'], claim['proof'], 0)
    tx.info()
    assert 'Claimed' in tx.events
    assert dai.balanceOf(account) == Wei(claim['amount'])

    with brownie.reverts('MerkleDistributor: Drop already claimed.'):
        tx = distributor.claim(claim['index'], account, claim['amount'], claim['proof'], 0)

    with brownie.reverts('MerkleDistributor: Invalid proof.'):
        tx = distributor.claim(123, ychad, '1000000 ether', claim['proof'], 0)
