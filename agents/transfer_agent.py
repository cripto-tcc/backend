from services.lifi_service import TOKEN_INFO, fetch_and_store_tokens


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


def create_transaction_data(from_address, to_address, token_symbol, amount, chain):
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
        "estimatedGas": "21000",  # Gas padrão para transferência
        "gasCosts": {
            "estimatedGas": "21000",
            "amountUSD": "5.50",  # Estimativa de gas em USD
            "symbol": "ETH"
        },
        "executionDuration": 30,  # Tempo estimado em segundos
        "tool": "transfer",
        "transactionRequest": {
            "to": to_address,
            "value": hex(int(amount_in_wei)),
            "from": from_address,
            "chainId": chain_upper,
            "gas": "21000",
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
        transfer_data = create_transaction_data(
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