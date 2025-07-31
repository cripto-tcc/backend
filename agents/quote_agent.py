def filter_quote_fields(quote):
    # Extrai apenas os campos essenciais para evitar alucinação do modelo
    filtered = {}
    if 'fromToken' in quote:
        filtered['fromToken'] = quote['fromToken']
    if 'toToken' in quote:
        filtered['toToken'] = quote['toToken']
    if 'fromAmount' in quote:
        filtered['fromAmount'] = quote['fromAmount']
    if 'toAmount' in quote:
        filtered['toAmount'] = quote['toAmount']
    if 'estimatedGas' in quote:
        filtered['estimatedGas'] = quote['estimatedGas']
    if 'gasCosts' in quote:
        filtered['gasCosts'] = quote['gasCosts']
    if 'tool' in quote:
        filtered['tool'] = quote['tool']
    if 'estimate' in quote:
        filtered['estimate'] = quote['estimate']
    return filtered

from services.lifi_service import LifiService, TOKEN_INFO, convert_quote_to_human_readable
from services.lifi_service import fetch_and_store_tokens


class QuoteAgent:
    def __init__(self):
        self.lifi_service = LifiService()

    async def get_quote(self, user_request, extracted_data):
        chain = user_request.chain
        # Busca e armazena os tokens da rede antes de qualquer coisa
        try:
            await fetch_and_store_tokens(chain)
        except Exception as e:
            return {"error": f"Erro ao buscar tokens da rede {chain}. Tente novamente."}
        
        quote = await self.lifi_service.get_quote(user_request, extracted_data)
        
        # Verifica se a cotação falhou
        if "error" in quote:
            return quote
            
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
        
        quote = convert_quote_to_human_readable(quote, from_token_decimals, to_token_decimals)
        quote = filter_quote_fields(quote)
        return quote
