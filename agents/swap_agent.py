from services.lifi_service import LifiService, TOKEN_INFO, convert_quote_to_human_readable
from services.lifi_service import fetch_and_store_tokens


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


def filter_swap_fields(swap_data):
    # Extrai apenas os campos essenciais para evitar alucinação do modelo
    filtered = {}
    if 'transactionRequest' in swap_data:
        filtered['transactionRequest'] = swap_data['transactionRequest']
    if 'fromToken' in swap_data:
        filtered['fromToken'] = swap_data['fromToken']
    if 'toToken' in swap_data:
        filtered['toToken'] = swap_data['toToken']
    if 'fromAmount' in swap_data:
        filtered['fromAmount'] = swap_data['fromAmount']
    if 'toAmount' in swap_data:
        filtered['toAmount'] = swap_data['toAmount']
    if 'estimatedGas' in swap_data:
        filtered['estimatedGas'] = swap_data['estimatedGas']
    if 'gasCosts' in swap_data:
        filtered['gasCosts'] = swap_data['gasCosts']
    if 'tool' in swap_data:
        filtered['tool'] = swap_data['tool']
    if 'estimate' in swap_data:
        filtered['estimate'] = swap_data['estimate']
    return filtered

class SwapAgent:
    def __init__(self):
        self.lifi_service = LifiService()

    async def get_swap(self, user_request, extracted_data):
        chain = user_request.chain
        # Busca e armazena os tokens da rede antes de qualquer coisa
        try:
            await fetch_and_store_tokens(chain)
        except Exception as e:
            return {"error": f"Erro ao buscar tokens da rede {chain}. Tente novamente."}

        swap_data = await self.lifi_service.get_swap_quote(user_request, extracted_data)

        # Verifica se o swap falhou
        if "error" in swap_data:
            return swap_data

        # Descobre os decimais dos tokens para conversão
        chain_upper = chain.upper()
        from_token = extracted_data.get("fromToken", "").upper()
        to_token = extracted_data.get("toToken", "").upper()

        # Verifica se os tokens foram encontrados
        from_token_info = TOKEN_INFO.get(chain_upper, {}).get(from_token)
        to_token_info = TOKEN_INFO.get(chain_upper, {}).get(to_token)

        if not from_token_info:
            return {"error": f"Token {from_token} não encontrado na rede {chain}."}
        if not to_token_info:
            return {"error": f"Token {to_token} não encontrado na rede {chain}."}

        from_token_decimals = from_token_info.get("decimals", 6)
        to_token_decimals = to_token_info.get("decimals", 6)

        swap_data = convert_quote_to_human_readable(swap_data, from_token_decimals, to_token_decimals)
        
        # Adiciona informação sobre tokens nativos se transactionRequest existir
        if 'transactionRequest' in swap_data:
            # Verifica se o token de origem é nativo
            is_from_native = is_native_token(from_token, chain)
            swap_data['transactionRequest']['isNativeToken'] = is_from_native
            
            # Adiciona informações do token de origem
            swap_data['transactionRequest']['fromTokenInfo'] = {
                "contract": from_token_info.get("address", ""),
                "decimals": from_token_info.get("decimals", 6),
                "name": from_token_info.get("name", from_token)
            }

        swap_data = filter_swap_fields(swap_data)
        
        # Retorna dados estruturados para o frontend
        return {
            "type": "swap_data",
            "data": swap_data,
            "message": "Dados da transação preparados com sucesso"
        }