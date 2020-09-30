import json
from brownie import MerkleDistributor, accounts, interface


def main():
    with open('snapshot/07-merkle-distribution.json') as fp:
        tree = json.load(fp)

    ychad = accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52")

    dai = interface.ERC20('0x6B175474E89094C44Da98b954EedeAC495271d0F')
    distributor = MerkleDistributor.deploy(dai, tree['merkleRoot'], {'from': ychad})

    dai.transfer(distributor, tree['tokenTotal'], {'from': ychad})

    for i, (address, claim) in enumerate(tree['claims'].items()):
        if not i % 50:
            print(f"Distribution in progress, {i} / {len(tree['claims'])}...")

        balance = dai.balanceOf(address)
        distributor.claim(
            claim['index'], address, claim['amount'], claim['proof'], 0, {'from': ychad}
        )

        assert dai.balanceOf(address) == balance + claim['amount']

    assert dai.balanceOf(distributor) == 0

    print("Distribution was successful!")
