import json
import pytest


@pytest.fixture()
def ychad(accounts):
    return accounts[-1]


@pytest.fixture()
def dai(interface):
    return interface.ERC20('0x6B175474E89094C44Da98b954EedeAC495271d0F')


@pytest.fixture()
def tree():
    return json.load(open('snapshot/07-merkle-distribution.json'))


@pytest.fixture()
def distributor(MerkleDistributor, ychad, tree, dai):
    return MerkleDistributor.deploy(str(dai), tree['merkleRoot'], {'from': ychad})
