from services.lifi_service import LifiService, TOKEN_INFO, convert_quote_to_human_readable
from services.lifi_service import fetch_and_store_tokens

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
        await fetch_and_store_tokens(chain)
        swap_data = await self.lifi_service.get_swap_quote(user_request, extracted_data)
        # Descobre os decimais dos tokens para conversão
        chain_upper = chain.upper()
        from_token = extracted_data.get("fromToken", "").upper()
        to_token = extracted_data.get("toToken", "").upper()
        from_token_decimals = TOKEN_INFO.get(chain_upper, {}).get(from_token, {}).get("decimals", 6)
        to_token_decimals = TOKEN_INFO.get(chain_upper, {}).get(to_token, {}).get("decimals", 6)
        swap_data = convert_quote_to_human_readable(swap_data, from_token_decimals, to_token_decimals)
        swap_data = filter_swap_fields(swap_data)
        return swap_data