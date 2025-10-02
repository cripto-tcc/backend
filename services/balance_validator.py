"""
Serviço para validação de saldos de tokens em diferentes redes blockchain.
Centraliza a lógica de consulta de saldo e validação para uso por múltiplos agentes.
"""

import aiohttp
import json
from services.lifi_service import TOKEN_INFO, get_gas_price


async def get_token_balance(wallet_address, token_address, token_decimals, chain, is_native=False):
    """
    Consulta o saldo de um token específico na carteira usando APIs públicas
    """
    try:
        # URLs das APIs RPC públicas por chain
        rpc_urls = {
            "ETH": "https://eth.llamarpc.com",
            "BAS": "https://mainnet.base.org", 
            "POL": "https://polygon.llamarpc.com"
        }
        
        chain_upper = chain.upper()
        rpc_url = rpc_urls.get(chain_upper)
        
        if not rpc_url:
            return {"error": f"Chain {chain} não suportada para consulta de saldo"}
        
        if is_native:
            # Para tokens nativos, usa eth_getBalance
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [wallet_address, "latest"],
                "id": 1
            }
        else:
            # Para tokens ERC-20, usa eth_call para balanceOf
            # balanceOf(address) = 0x70a08231 + endereço (32 bytes padded)
            address_param = wallet_address[2:].zfill(64)  # Remove 0x e pad com zeros
            data = f"0x70a08231{address_param}"
            
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{
                    "to": token_address,
                    "data": data
                }, "latest"],
                "id": 1
            }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                rpc_url, 
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    return {"error": f"Erro na API: {response.status}"}
                
                data = await response.json()
                
                if "error" in data:
                    return {"error": f"Erro RPC: {data['error'].get('message', 'Desconhecido')}"}
                
                # Converte resultado hex para decimal
                balance_hex = data.get("result", "0x0")
                balance_wei = int(balance_hex, 16)
                
                # Converte para unidade legível
                balance_decimal = balance_wei / (10 ** token_decimals)
                
                return {
                    "balance_wei": str(balance_wei),
                    "balance_decimal": balance_decimal,
                    "balance_formatted": f"{balance_decimal:.6f}".rstrip('0').rstrip('.')
                }
                
    except Exception as e:
        return {"error": f"Erro ao consultar saldo: {str(e)}"}


def is_native_token(token_symbol, chain):
    """
    Verifica se o token é nativo da rede
    """
    native_tokens = {
        "ETH": ["ETH"],
        "BAS": ["ETH"],
        "POL": ["MATIC"]
    }

    chain_upper = chain.upper()
    return token_symbol.upper() in native_tokens.get(chain_upper, [])


def get_estimated_gas(chain, is_native):
    """
    Retorna estimativa de gas baseada na rede e tipo de token, em formato HEX
    """
    base_gas = {
        "ETH": 21000,    # Ethereum
        "BAS": 21000,    # Base (L2 da Ethereum)
        "POL": 21000     # Polygon
    }

    # Gas para transferências de tokens ERC-20 (se não for nativo)
    erc20_gas = {
        "ETH": 65000,    # Ethereum
        "BAS": 65000,    # Base
        "POL": 65000     # Polygon
    }

    chain_upper = chain.upper()
    if is_native:
        gas_value = base_gas.get(chain_upper, 21000)
    else:
        gas_value = erc20_gas.get(chain_upper, 65000)
    return hex(gas_value)


async def get_gas_price_with_validation(chain):
    """
    Busca gas price da API e valida a resposta
    """
    gas_price_data = await get_gas_price(chain)
    if "error" in gas_price_data:
        return {"error": f"Erro ao buscar gas price: "
                f"{gas_price_data['error']}"}

    gas_price = gas_price_data.get("gasPrice")
    if not gas_price:
        return {"error": "Gas price não encontrado na resposta da API"}

    return {"gasPrice": gas_price}


async def validate_sufficient_balance(wallet_address, token_symbol, amount, chain, include_gas_fee=False):
    """
    Valida se a carteira tem saldo suficiente para a operação solicitada.
    
    Args:
        wallet_address: Endereço da carteira
        token_symbol: Símbolo do token (ETH, USDC, etc.)
        amount: Quantidade a ser transferida/swapada
        chain: Rede blockchain (ETH, BAS, POL)
        include_gas_fee: Se deve considerar gas fee no cálculo (True para transfers de tokens nativos)
    
    Returns:
        dict: {"success": bool, "error": str, "balance_info": dict}
    """
    try:
        # Busca informações do token
        chain_upper = chain.upper()
        token_info = TOKEN_INFO.get(chain_upper, {}).get(token_symbol.upper())
        
        if not token_info:
            return {
                "success": False,
                "error": f"Token {token_symbol} não encontrado na rede {chain}."
            }
        
        # Verifica se é token nativo
        is_native = is_native_token(token_symbol, chain)
        
        # Consulta saldo atual da carteira
        balance_result = await get_token_balance(
            wallet_address,
            token_info["address"], 
            token_info["decimals"],
            chain,
            is_native
        )
        
        if "error" in balance_result:
            return {
                "success": False,
                "error": f"Não foi possível verificar o saldo: {balance_result['error']}"
            }
        
        # Valida se tem saldo suficiente
        current_balance = balance_result["balance_decimal"]
        requested_amount = float(amount)
        
        if current_balance < requested_amount:
            return {
                "success": False,
                "error": f"Saldo insuficiente. Você tem {balance_result['balance_formatted']} {token_symbol.upper()}, mas tentou operar {requested_amount} {token_symbol.upper()}.",
                "balance_info": balance_result
            }
        
        # Para tokens nativos, considera também o gas fee se solicitado
        if is_native and include_gas_fee:
            gas_price_result = await get_gas_price_with_validation(chain)
            if "error" not in gas_price_result:
                gas_price = gas_price_result["gasPrice"]
                estimated_gas = get_estimated_gas(chain, is_native)
                
                # Calcula gas em decimal
                gas_price_decimal = int(gas_price, 16) / (10 ** 18)
                gas_limit_decimal = int(estimated_gas, 16)
                total_gas_cost = gas_price_decimal * gas_limit_decimal
                
                # Verifica se tem saldo para operação + gas
                if current_balance < (requested_amount + total_gas_cost):
                    return {
                        "success": False,
                        "error": f"Saldo insuficiente considerando gas fee. Você precisa de aproximadamente {total_gas_cost:.6f} {token_symbol.upper()} adicional para o gas. Saldo atual: {balance_result['balance_formatted']} {token_symbol.upper()}.",
                        "balance_info": balance_result
                    }
        
        return {
            "success": True,
            "balance_info": balance_result
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Erro ao validar saldo: {str(e)}"
        }