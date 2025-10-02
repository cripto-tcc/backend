from services.lifi_service import (
    TOKEN_INFO,
    fetch_and_store_tokens,
    get_gas_price
)
from services.balance_validator import validate_sufficient_balance, is_native_token, get_estimated_gas, get_gas_price_with_validation
import aiohttp


def validate_wallet_address(address):
    """
    Valida se o endereço da carteira está no formato correto.
    Para ETH, Polygon e Base, deve ter exatamente 42 caracteres (0x + 40 hex).
    """
    if not address:
        return False, "Endereço não fornecido."
    
    if not isinstance(address, str):
        return False, "Endereço deve ser uma string."
    
    # Remove espaços em branco
    address = address.strip()
    
    # Verifica se tem exatamente 42 caracteres
    if len(address) != 42:
        return False, f"Endereço deve ter exatamente 42 caracteres. Fornecido: {len(address)} caracteres."
    
    # Verifica se começa com '0x'
    if not address.startswith('0x'):
        return False, "Endereço deve começar com '0x'."
    
    # Verifica se os 40 caracteres após '0x' são hexadecimais
    hex_part = address[2:]
    if not all(c in '0123456789abcdefABCDEF' for c in hex_part):
        return False, "Endereço contém caracteres inválidos. Deve conter apenas números e letras A-F."
    
    return True, "Endereço válido."


async def get_native_token_price_usd(chain):
    """
    Busca preço do token nativo da rede em USD usando CoinGecko API
    """
    # Mapeamento de chains para IDs do CoinGecko
    chain_to_coingecko = {
        "ETH": "ethereum",      # ETH
        "BAS": "ethereum",      # Base usa ETH
        "POL": "matic-network"  # MATIC
    }

    chain_upper = chain.upper()
    coingecko_id = chain_to_coingecko.get(chain_upper)

    if not coingecko_id:
        return 0

    url = (f"https://api.coingecko.com/api/v3/simple/price?"
            f"ids={coingecko_id}&vs_currencies=usd")

    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=10) as response:
            data = await response.json()
            price = data.get(coingecko_id, {}).get("usd", 0)
            return price


def calculate_gas_cost_usd(gas_price, estimated_gas, token_price_usd=0):
    """
    Calcula o custo do gas em USD
    estimated_gas deve estar em hexadecimal (ex: '0x5208')
    """
    gas_price_decimal = int(gas_price, 16)
    gas_price_eth = float(gas_price_decimal) / (10 ** 18)

    estimated_gas_decimal = int(estimated_gas, 16)

    # Calcula custo total em ETH
    total_gas_eth = gas_price_eth * estimated_gas_decimal
    # Calcula custo total em USD
    total_cost_usd = total_gas_eth * token_price_usd
    return str(round(total_cost_usd, 6))


async def create_transaction_data(
    from_address, to_address, token_symbol, amount, chain
):
    """
    Cria dados de transação artificiais para transferência
    Seguindo o formato do LI.FI mas sem bater na API
    """
    # Busca informações do token
    chain_upper = chain.upper()
    token_info = TOKEN_INFO.get(chain_upper, {}).get(token_symbol.upper())

    if not token_info:
        return {"error": f"Token {token_symbol} não encontrado na rede "
                f"{chain}."}

    token_address = token_info["address"]
    token_decimals = token_info["decimals"]

    # Verifica se é token nativo
    is_native = is_native_token(token_symbol, chain)

    # Converte o valor para wei/smallest unit
    try:
        amount_in_wei = str(int(float(amount) * (10 ** token_decimals)))
    except Exception:
        return {"error": "Valor de quantidade inválido."}

    # Busca gas price real da API
    gas_price_result = await get_gas_price_with_validation(chain)
    if "error" in gas_price_result:
        return gas_price_result

    gas_price = gas_price_result["gasPrice"]

    # Calcula gas estimado dinamicamente
    estimated_gas = get_estimated_gas(chain, is_native)

    # Busca preço do token nativo da rede em USD
    token_price_usd = await get_native_token_price_usd(chain)

    gas_cost_usd = calculate_gas_cost_usd(
        gas_price, estimated_gas, token_price_usd
    )

    # Cria dados de transação artificiais
    transaction_data = {
        "fromToken": token_symbol.upper(),
        "toToken": token_symbol.upper(),  # Mesmo token para transferência
        "fromAmount": float(amount),
        "toAmount": float(amount),  # Mesmo valor para transferência
        "fromAddress": from_address,
        "toAddress": to_address,
        "tokenAddress": token_address,
        "tokenDecimals": token_decimals,
        "estimatedGas": estimated_gas,  # Gas calculado dinamicamente
        "gasCosts": {
            "estimatedGas": estimated_gas,
            "amountUSD": gas_cost_usd,  # Custo calculado dinamicamente
            "symbol": "ETH" if chain_upper in ["ETH", "BAS"] else "MATIC"
        },
        "executionDuration": 30,  # Tempo estimado em segundos
        "tool": "transfer",
        "transactionRequest": {
            "to": to_address,
            "value": hex(int(amount_in_wei)),
            "from": from_address,
            "chainId": chain_upper,
            "gas": estimated_gas,
            "gasLimit": estimated_gas, # 
            "gasPrice": gas_price,
            "isNativeToken": is_native,
            "fromTokenInfo": {
                "contract": token_address,
                "decimals": token_decimals,
                "name": token_info.get("name", token_symbol.upper())
            }
        }
    }

    return transaction_data


class TransferAgent:
    def __init__(self):
        pass

    async def get_transfer(self, user_request, extracted_data):
        chain = user_request.chain
        # Busca e armazena os tokens da rede antes de qualquer coisa
        try:
            await fetch_and_store_tokens(chain)
        except Exception:
            return {"error": f"Erro ao buscar tokens da rede {chain}. "
                    "Tente novamente."}

        # Extrai dados da transferência
        from_address = user_request.walletAddress
        to_address = extracted_data.get("toAddress", "")
        token_symbol = extracted_data.get("token", "").upper()
        amount = extracted_data.get("amount", "")

        if not to_address:
            return {"error": "Endereço de destino não encontrado."}
        if not token_symbol:
            return {"error": "Token não especificado."}
        if not amount:
            return {"error": "Quantidade não especificada."}

        # Valida o endereço de destino
        is_valid, validation_message = validate_wallet_address(to_address)
        if not is_valid:
            return {"error": f"Endereço de destino inválido: {validation_message}"}

        # Valida se tem saldo suficiente (incluindo gas fee para tokens nativos)
        is_native = is_native_token(token_symbol, chain)
        balance_validation = await validate_sufficient_balance(
            from_address, 
            token_symbol, 
            amount, 
            chain, 
            include_gas_fee=is_native  # Considera gas fee apenas para tokens nativos
        )
        
        if not balance_validation["success"]:
            return {"error": balance_validation["error"]}

        # Cria dados de transação
        transfer_data = await create_transaction_data(
            from_address,
            to_address,
            token_symbol,
            amount,
            chain
        )

        # Verifica se houve erro na criação dos dados
        if "error" in transfer_data:
            return transfer_data

        # Retorna dados estruturados para o frontend
        return {
            "type": "transfer_data",
            "data": transfer_data,
            "message": "Dados da transferência preparados com sucesso"
        }
