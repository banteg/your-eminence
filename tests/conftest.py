import json
import pytest


@pytest.fixture(autouse=True)
def isolation_setup(fn_isolation):
    # enable function isolation
    pass


@pytest.fixture(scope="session")
def ychad(accounts):
    # the hero of our story
    return accounts[-1]


@pytest.fixture(scope="module")
def dai(interface):
    return interface.ERC20('0x6B175474E89094C44Da98b954EedeAC495271d0F')


@pytest.fixture(scope="session")
def tree():
    with open('snapshot/07-merkle-distribution.json') as fp:
        claim_data = json.load(fp)
    for value in claim_data['claims'].values():
        value['amount'] = int(value['amount'], 16)

    return claim_data


@pytest.fixture(scope="module")
def distributor(MerkleDistributor, ychad, tree, dai):
    contract = MerkleDistributor.deploy(dai, tree['merkleRoot'], {'from': ychad})
    dai.transfer(contract, tree['tokenTotal'], {'from': ychad})

    return contract
