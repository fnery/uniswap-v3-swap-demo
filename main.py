"""
This script implements a purchase of `OUT_AMOUNT_READABLE` units of "token0" from
the `POOL_ADDRESS` pool with a maximum allowed slippage `MAX_SLIPPAGE`.

This is just for demo purposes. _Don't_ use this to trade tokens with any value!

"""

import os
from web3 import Web3
from dotenv import load_dotenv

# User parameters
OUT_AMOUNT_READABLE = 0.01
POOL_ADDRESS = "0x41E3F1A4F715A5C05b1B90144902db17CA91BF5c"
MAX_SLIPPAGE = 0.1

# Other constants
load_dotenv()
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PROVIDER = os.getenv("PROVIDER")
WALLET_ADDRESS = os.getenv("ADDRESS")

POOL_ABI_PATH = "UniswapV3PoolABI.json"
QUOTER_ADDRESS = "0xEd1f6473345F45b75F8179591dd5bA1888cf2FB3"
QUOTER_ABI_PATH = "UniswapV3QuoterV2ABI.json"
ROUTER_ADDRESS = "0x3bFA4769FB09eefC5a80d6E87c3B9C650f7Ae48E"
ROUTER_ABI_PATH = "UniswapV3SwapRouter02ABI.json"
ERC20_ABI_PATH = "ERC20ABI.json"


def load_abi(abi_path):
    with open(abi_path, "r") as file:
        return file.read()


def success_status(tx_receipt):
    return "successful" if tx_receipt.status == 1 else "failed"


if __name__ == "__main__":
    web3 = Web3(Web3.HTTPProvider(PROVIDER))
    print(f"web3 connection {'successful' if web3.is_connected() else 'failed'}")

    pool = web3.eth.contract(address=POOL_ADDRESS, abi=load_abi(POOL_ABI_PATH))
    fee = pool.functions.fee().call()
    sqrtPriceX96 = pool.functions.slot0().call()[0]

    # Assume token going "out" of the pool (being purchased) is token0
    out_address = pool.functions.token0().call()
    out_contract = web3.eth.contract(address=out_address, abi=load_abi(ERC20_ABI_PATH))
    out_symbol = out_contract.functions.symbol().call()
    out_decimals = out_contract.functions.decimals().call()
    out_amount = int(OUT_AMOUNT_READABLE * 10**out_decimals)
    out_price = (sqrtPriceX96 / (2**96)) ** 2  # price of token0 in terms of token1

    # Assume token going "in" to the pool (being sold) is token1
    in_address = pool.functions.token1().call()
    in_contract = web3.eth.contract(address=in_address, abi=load_abi(ERC20_ABI_PATH))
    in_symbol = in_contract.functions.symbol().call()
    in_decimals = in_contract.functions.decimals().call()
    in_amount = int(out_amount * out_price)
    in_amount_readable = in_amount / 10**in_decimals

    print(
        f"Goal: Buy {OUT_AMOUNT_READABLE} {out_symbol} (worth {in_amount_readable} {in_symbol})"
    )

    quoter = web3.eth.contract(address=QUOTER_ADDRESS, abi=load_abi(QUOTER_ABI_PATH))
    quote = quoter.functions.quoteExactOutputSingle(
        [
            in_address,
            out_address,
            out_amount,
            fee,
            0,  # sqrtPriceLimitX96: a value of 0 makes this parameter inactive
        ]
    ).call()

    in_amount_expected = quote[0]
    in_amount_expected_readable = in_amount_expected / 10**in_decimals

    price_impact = (in_amount_expected - in_amount) / in_amount

    print(
        f"Expected amount to pay: {in_amount_expected_readable} {in_symbol} (price impact: {price_impact:.2%})"
    )

    in_amount_max = int(out_amount * out_price * (1 + MAX_SLIPPAGE))
    in_amount_max_readable = in_amount_max / 10**in_decimals

    print(
        f"Max. amount to pay: {in_amount_max_readable} {in_symbol} (max. slippage: {MAX_SLIPPAGE:.2%})"
    )

    # Approval transaction
    transaction = in_contract.functions.approve(
        ROUTER_ADDRESS, in_amount_max
    ).build_transaction(
        {
            "chainId": web3.eth.chain_id,
            "gas": int(1e7),
            "gasPrice": web3.eth.gas_price,
            "nonce": web3.eth.get_transaction_count(WALLET_ADDRESS),
        }
    )
    signed_txn = web3.eth.account.sign_transaction(transaction, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print(
        f"Approval transaction {tx_receipt.transactionHash.hex()} {success_status(tx_receipt)}"
    )

    # Swap transactions
    router = web3.eth.contract(address=ROUTER_ADDRESS, abi=load_abi(ROUTER_ABI_PATH))
    transaction = router.functions.exactOutputSingle(
        [
            in_address,
            out_address,
            fee,
            WALLET_ADDRESS,
            out_amount,
            in_amount_max,
            0,  # sqrtPriceLimitX96: a value of 0 makes this parameter inactive
        ]
    ).build_transaction(
        {
            "chainId": web3.eth.chain_id,
            "gas": int(1e7),
            "gasPrice": web3.eth.gas_price,
            "nonce": web3.eth.get_transaction_count(WALLET_ADDRESS),
        }
    )
    signed_txn = web3.eth.account.sign_transaction(transaction, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print(
        f"Swap transaction {tx_receipt.transactionHash.hex()} {success_status(tx_receipt)}"
    )
