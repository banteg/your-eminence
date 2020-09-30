import brownie
from brownie.test import given, strategy


@given(st_claim=strategy("decimal", min_value=0, max_value="0.9999", places=4))
def test_claim(distributor, tree, dai, st_claim):
    idx = int(st_claim * len(tree["claims"]))
    account = sorted(tree["claims"])[idx]
    claim = tree['claims'][account]

    initial_balance = dai.balanceOf(account)
    distributor.claim(claim['index'], account, claim['amount'], claim['proof'], 0, {'from': account})

    assert dai.balanceOf(account) == initial_balance + claim['amount']


@given(
    st_claim=strategy("decimal", min_value=0, max_value="0.9999", places=4),
    st_account=strategy("address"),
)
def test_claim_via_different_account(distributor, tree, dai, st_claim, st_account):
    idx = int(st_claim * len(tree["claims"]))
    account = sorted(tree["claims"])[idx]
    claim = tree['claims'][account]

    initial_balance = dai.balanceOf(account)
    distributor.claim(
        claim['index'], account, claim['amount'], claim['proof'], 0, {'from': st_account}
    )

    assert dai.balanceOf(account) == initial_balance + claim['amount']


@given(st_claim=strategy("decimal", min_value=0, max_value="0.9999", places=4))
def test_claim_twice(distributor, tree, dai, st_claim):
    idx = int(st_claim * len(tree["claims"]))
    account = sorted(tree["claims"])[idx]
    claim = tree['claims'][account]

    distributor.claim(claim['index'], account, claim['amount'], claim['proof'], 0, {'from': account})

    with brownie.reverts('MerkleDistributor: Drop already claimed.'):
        distributor.claim(
            claim['index'], account, claim['amount'], claim['proof'], 0, {'from': account}
        )
