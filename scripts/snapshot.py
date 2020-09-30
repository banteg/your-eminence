import json
import os
from collections import Counter, defaultdict
from functools import wraps
from os.path import dirname, exists

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
ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'


def cached(path):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if exists(path):
                return json.load(open(path))
            else:
                result = func(*args, **kwargs)
                os.makedirs(dirname(path), exist_ok=True)
                with open(path, 'wt') as f:
                    f.write(result)
                return result

        return wrapper

    return decorator


@cached('snapshot/01-balances.json')
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


@cached('snapshot/02-burn-to-dai.json')
def step_02(balances):
    print('step 02. normalize balances to dai.')
    ensure_archive_node()

    dai_balances = Counter()  # user -> dai equivalent
    for name in balances:
        print(f'processing {name}')
        for user, balance in tqdm(balances[name].items()):
            token = TOKENS[name]
            tx = {'to': str(token), 'data': EMN.calculateContinuousBurnReturn.encode_input(balance)}
            out = decode_single('uint', web3.eth.call(tx, SNAPSHOT_BLOCK))
            if name in {'eCRV', 'eLINK', 'eAAVE', 'eYFI', 'eSNX'}:
                tx = {'to': str(EMN), 'data': EMN.calculateContinuousBurnReturn.encode_input(out)}
                out = decode_single('uint', web3.eth.call(tx, SNAPSHOT_BLOCK))
            dai_balances[user] += out

    dai_balances = valfilter(bool, dict(dai_balances.most_common()))
    dai_total = Wei(sum(dai_balances.values())).to('ether')
    print(f'equivalent value: {dai_total:,.0f} DAI')

    return dai_balances


def step_03(dai_balances):
    print('step 03. unwrap uniswap lp.')
    ensure_archive_node()
    for user, balance in tqdm(dai_balances.items()):
        if not web3.eth.getCode(user):
            continue
        print(f'{user} is a contract')


def main():
    balances = step_01()
    dai_balances = step_02(balances)
    step_03(dai_balances)
