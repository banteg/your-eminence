import os
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from os.path import dirname, exists

import toml
from brownie import Wei, interface, web3
from brownie.exceptions import VirtualMachineError
from eth_abi import decode_single
from eth_utils import address
from toolz import valfilter, valmap
from tqdm import tqdm, trange

START_BLOCK = 10950650
SNAPSHOT_BLOCK = 10954410
TOKENS = {
    'EMN': '0x5ade7ae8660293f2ebfcefaba91d141d72d221e8',
    'eCRV': '0xb387e90367f1e621e656900ed2a762dc7d71da8c',
    'eLINK': '0xe4ffd682380c571a6a07dd8f20b402412e02830e',
    'eAAVE': '0xc08f38f43adb64d16fe9f9efcc2949d9eddec198',
    'eYFI': '0xed35197cadf01fcbfe6cfc11081f299cffb095bf',
    'eSNX': '0xd77c2ab1cd0faa4b79e16a0e7472cb222a9ee175',
}

TOKENS = valmap(interface.EminenceCurrency, TOKENS)
EMN = TOKENS['EMN']
DAI = interface.ERC20('0x6B175474E89094C44Da98b954EedeAC495271d0F')
UNISWAP_FACTORY = '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f'
ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'


def cached(path):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if exists(path):
                print('load from cache', path)
                return toml.load(open(path))
            else:
                result = func(*args, **kwargs)
                os.makedirs(dirname(path), exist_ok=True)
                with open(path, 'wt') as f:
                    toml.dump(result, f)
                    print('cached', path)
                return result

        return wrapper

    return decorator


@cached('snapshot/01-balances.toml')
def step_01():
    print('step 01. snapshot token balances.')
    balances = defaultdict(Counter)  # token -> user -> balance
    for name, address in TOKENS.items():
        print(f'processing {name}')
        contract = web3.eth.contract(str(address), abi=EMN.abi)
        for start in trange(START_BLOCK, SNAPSHOT_BLOCK, 1000):
            end = min(start + 999, SNAPSHOT_BLOCK)
            logs = contract.events.Transfer().getLogs(fromBlock=start, toBlock=end)
            for log in logs:
                if log['args']['from'] != ZERO_ADDRESS:
                    balances[name][log['args']['from']] -= log['args']['value']
                if log['args']['to'] != ZERO_ADDRESS:
                    balances[name][log['args']['to']] += log['args']['value']
        assert min(balances[name].values()) >= 0, 'negative balances found'
        balances[name] = valfilter(bool, dict(balances[name].most_common()))

    return balances


def ensure_archive_node():
    fresh = web3.eth.call({'to': str(EMN), 'data': EMN.totalSupply.encode_input()})
    old = web3.eth.call({'to': str(EMN), 'data': EMN.totalSupply.encode_input()}, SNAPSHOT_BLOCK)
    assert fresh != old, 'this step requires an archive node'


def convert_to_dai(name, balance):
    token = TOKENS[name]
    tx = {'to': str(token), 'data': EMN.calculateContinuousBurnReturn.encode_input(balance)}
    dai = decode_single('uint', web3.eth.call(tx, SNAPSHOT_BLOCK))
    if name in {'eCRV', 'eLINK', 'eAAVE', 'eYFI', 'eSNX'}:
        tx = {'to': str(EMN), 'data': EMN.calculateContinuousBurnReturn.encode_input(dai)}
        dai = decode_single('uint', web3.eth.call(tx, SNAPSHOT_BLOCK))
    return dai


@cached('snapshot/02-burn-to-dai.toml')
def step_02(balances):
    print('step 02. normalize balances to dai.')
    ensure_archive_node()

    dai_balances = Counter()  # user -> dai equivalent
    for name in balances:
        print(f'processing {name}')
        pool = ThreadPoolExecutor(10)
        futures = pool.map(partial(convert_to_dai, name), balances[name].values())
        for user, dai in tqdm(zip(balances[name], futures), total=len(balances[name])):
            dai_balances[user] += dai

    dai_balances = valfilter(bool, dict(dai_balances.most_common()))
    dai_total = Wei(sum(dai_balances.values())).to('ether')
    print(f'equivalent value: {dai_total:,.0f} DAI')

    return dai_balances


@cached('snapshot/03-contracts.toml')
def step_03(balances):
    print('step 03. contract addresses.')
    pool = ThreadPoolExecutor(10)
    codes = pool.map(web3.eth.getCode, balances)
    contracts = {user: balances[user] for user, code in tqdm(zip(balances, codes), total=len(balances)) if code}
    print(f'{len(contracts)} contracts found')
    return contracts


def main():
    balances = step_01()
    dai_balances = step_02(balances)
    contracts = step_03(dai_balances)
