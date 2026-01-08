#{'timestamp': row['timestamp'], 'token': token, 'capacity': capacity, 'ft_apy_30d': row['col1_asset'], 'token_apr': row['col3_ot'], 'tvl': tvl}
from app.config import configuration
from app.yield_basis.ABIs import ABIs
from app import logger
from web3 import Web3
from app.yield_basis.smart_api import deposit_to_vault
from typing import Dict

class DepositExecutor:
    def __init__(self):
        self.alchemy_url = configuration.ALCHEMY_URL_ETH
    
    async def deposit_max(self, currect_data: Dict):
        try:
            logger.info(f"Deposit starts to fill this pool: {currect_data}")

            # Connect to Etherium via Alchemy
            eth_net = Web3(Web3.HTTPProvider(self.alchemy_url))

            # Check if the connection is successful
            if eth_net.is_connected():
                logger.info("Connected to ETH network")
            else:
                logger.info("Connection problems")

            # Define contract address and ABI
            leverage_contract_adress = ''
            leverage_contract_abi = ''
            pool_contract_adress = ''
            pool_contract_abi = ''
            token_contract_adress = ''
            token_contract_abi = ''
            
            if currect_data['token'] == 'cbBTC':
                leverage_contract_adress = configuration.YIELDBASIS_cbBTC_Leverage
                leverage_contract_abi = ABIs['YIELDBASIS_cbBTC_Leverage']
                pool_contract_adress = configuration.YIELDBASIS_cbBTC_POOL
                pool_contract_abi = ABIs['YIELDBASIS_cbBTC_POOL']
                token_contract_adress = configuration.Token_cbBTC
                token_contract_abi = ABIs['YIELDBASIS_cbBTC_POOL']
            elif currect_data['token'] == 'WBTC':
                leverage_contract_adress = configuration.YIELDBASIS_WBTC_Leverage
                leverage_contract_abi = ABIs['YIELDBASIS_WBTC_Leverage']
                pool_contract_adress = configuration.YIELDBASIS_WBTC_POOL
                pool_contract_abi = ABIs['YIELDBASIS_WBTC_POOL']
            elif currect_data['token'] == 'tBTC':
                leverage_contract_adress = configuration.YIELDBASIS_tBTC_Leverage
                leverage_contract_abi = ABIs['YIELDBASIS_tBTC_Leverage']
                pool_contract_adress = configuration.YIELDBASIS_tBTC_POOL
                pool_contract_abi = ABIs['YIELDBASIS_tBTC_POOL']
            elif currect_data['token'] == 'WETH':
                leverage_contract_adress = configuration.YIELDBASIS_WETH_Leverage
                leverage_contract_abi = ABIs['YIELDBASIS_WETH_Leverage']
                pool_contract_adress = configuration.YIELDBASIS_WETH_POOL
                pool_contract_abi = ABIs['YIELDBASIS_WETH_POOL']

            # Load the leverage contract
            leverage_contract = eth_net.eth.contract(address=leverage_contract_adress, abi=leverage_contract_abi)
            logger.info(f"Loaded leverage contract: {leverage_contract}")

            return
    
        except Exception as e:
            # Catch any exception
            logger.error(f"Error: {e}")