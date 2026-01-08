from web3 import Web3
from decimal import Decimal
import json
from app.yield_basis.ABIs import ABIs
from app.config import configuration
import time
from datetime import datetime
from app import logger

def get_smart_contract_data():
    try:
        # Connect to Etherium via Alchemy
        eth_net = Web3(Web3.HTTPProvider(configuration.ALCHEMY_URL_ETH))

        # Check if the connection is successful
        if eth_net.is_connected():
            logger.info("Connected to ETH network")
        else:
            logger.info("Connection problems")

        # Load the contract
        pool_contract = eth_net.eth.contract(address=configuration.YIELDBASIS_cbBTC_POOL, abi=ABIs['YIELDBASIS_cbBTC_POOL'])
        x = pool_contract.functions.user_supply().call()
        print(x)
        #pool_count = position_manager_contract.functions.balanceOf(arb_address).call()
        
        
    except Exception as e:
        # Catch any exception
        logger.error(f"Error: {e}")
        
    finally:
        # Delay after failure before recovery
        time.sleep(10)


def deposit_to_vault(w3, contract, assets_amount, debt_amount, slippage_tolerance=0.01):
    """
    Deposit assets to the vault.
    
    Args:
        assets_amount: Amount of BTC (or similar) to deposit in human-readable units (e.g., 0.5 for 0.5 BTC)
        debt_amount: Amount of debt/stablecoin in human-readable units (e.g., 50000 for $50,000)
        slippage_tolerance: Acceptable slippage (default 1%)
    """

    # Account
    private_key = 'YOUR_PRIVATE_KEY'
    account = w3.eth.account.from_key(private_key)
    
    # Get token decimals (usually 18 for most tokens, 8 for WBTC)
    asset_decimals = 8  # Adjust based on your asset token (WBTC = 8, most others = 18)
    debt_decimals = 18  # Stablecoin decimals (usually 18)
    
    # Convert to wei/smallest unit
    assets_wei = int(Decimal(str(assets_amount)) * Decimal(10 ** asset_decimals))
    debt_wei = int(Decimal(str(debt_amount)) * Decimal(10 ** debt_decimals))
    
    # Calculate expected shares (simplified - you should calculate this based on contract state)
    # For first deposit: shares ≈ value_after (in USD terms)
    # For subsequent deposits: shares = supply * value_after / value_before - supply
    # Here we use a simplified calculation with slippage protection
    expected_shares = debt_wei  # Rough approximation
    min_shares = int(expected_shares * (1 - slippage_tolerance))
    
    # Receiver address (optional, defaults to msg.sender)
    receiver = account.address  # or specify another address
    
    # Step 1: Approve asset token spending
    asset_token_address = 'ASSET_TOKEN_ADDRESS'  # e.g., WBTC
    asset_token_abi = [...]  # ERC20 ABI
    asset_token = w3.eth.contract(address=asset_token_address, abi=asset_token_abi)
    
    approve_tx = asset_token.functions.approve(
        contract_address,
        assets_wei
    ).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 100000,
        'gasPrice': w3.eth.gas_price
    })
    
    signed_approve = w3.eth.account.sign_transaction(approve_tx, private_key)
    approve_hash = w3.eth.send_raw_transaction(signed_approve.raw_transaction)
    print(f"Approval tx: {approve_hash.hex()}")
    w3.eth.wait_for_transaction_receipt(approve_hash)
    
    # Step 2: The AMM needs to approve stablecoin - this is likely done by the contract
    # You may need to ensure the AMM has proper approvals set up beforehand
    
    # Step 3: Call deposit function
    deposit_tx = contract.functions.deposit(
        assets_wei,      # assets: uint256
        debt_wei,        # debt: uint256
        min_shares,      # min_shares: uint256
        receiver         # receiver: address (optional, can omit to use msg.sender)
    ).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 500000,  # Estimate gas or use eth_estimateGas
        'gasPrice': w3.eth.gas_price
    })
    
    signed_deposit = w3.eth.account.sign_transaction(deposit_tx, private_key)
    deposit_hash = w3.eth.send_raw_transaction(signed_deposit.raw_transaction)
    print(f"Deposit tx: {deposit_hash.hex()}")
    
    # Wait for transaction receipt
    receipt = w3.eth.wait_for_transaction_receipt(deposit_hash)
    print(f"Transaction successful! Gas used: {receipt['gasUsed']}")
    
    # Parse the Deposit event to get shares received
    deposit_event = contract.events.Deposit().process_receipt(receipt)
    if deposit_event:
        shares_received = deposit_event[0]['args']['shares']
        print(f"Shares received: {shares_received / 10**18}")
    
    return receipt