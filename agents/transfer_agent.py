from services.lifi_service import (
    TOKEN_INFO,
    fetch_and_store_tokens,
    get_gas_price
)
import aiohttp


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
    Retorna estimativa de gas baseada na rede e tipo de token
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
        return str(base_gas.get(chain_upper, 21000))
    else:
        return str(erc20_gas.get(chain_upper, 65000))


def calculate_gas_cost_usd(gas_price, estimated_gas, token_price_usd=0):
    """
    Calcula o custo do gas em USD
    """
    gas_price_decimal = int(gas_price, 16)
    gas_price_eth = float(gas_price_decimal) / (10 ** 18)

    # Calcula custo total em ETH
    total_gas_eth = gas_price_eth * float(estimated_gas)
    # Calcula custo total em USD
    total_cost_usd = total_gas_eth * token_price_usd
    return str(round(total_cost_usd, 6))


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
