import brownie
from brownie.test import given, strategy
from hypothesis import assume


@given(
    st_claim=strategy("decimal", min_value=0, max_value="0.9999", places=4),
    st_tip=strategy("uint", min_value=0, max_value=10000),
    )
def test_claim(distributor, tree, dai, st_claim, st_tip, ychad):
    idx = int(st_claim * len(tree["claims"]))
    account = sorted(tree["claims"])[idx]
    claim = tree['claims'][account]

    initial_balance = dai.balanceOf(account)
    chad_balance = dai.balanceOf(ychad)
    expected_tip = claim['amount'] * st_tip // 10000

    distributor.claim(
        claim['index'], account, claim['amount'], claim['proof'], st_tip, {'from': account}
    )

    assert dai.balanceOf(account) == initial_balance + claim['amount'] - expected_tip
    assert dai.balanceOf(ychad) == chad_balance + expected_tip


@given(
    st_claim=strategy("decimal", min_value=0, max_value="0.9999", places=4),
    st_tip=strategy("uint", min_value=0, max_value=10000),
    st_account=strategy("address"),
)
def test_claim_via_different_account(distributor, tree, dai, ychad, st_claim, st_tip, st_account):
    idx = int(st_claim * len(tree["claims"]))
    account = sorted(tree["claims"])[idx]
    claim = tree['claims'][account]

    assume(account != st_account)

    initial_balance = dai.balanceOf(account)
    chad_balance = dai.balanceOf(ychad)
    distributor.claim(
        claim['index'], account, claim['amount'], claim['proof'], st_tip, {'from': st_account}
    )

    assert dai.balanceOf(account) == initial_balance + claim['amount']

    # because the claim was via another account, no tip is received
    assert dai.balanceOf(ychad) == chad_balance


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
