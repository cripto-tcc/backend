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

class QuoteAgent:
    def __init__(self):
        self.lifi_service = LifiService()

    async def get_quote(self, user_request, extracted_data):
        quote = await self.lifi_service.get_quote(user_request, extracted_data)
        # Descobre os decimais dos tokens para conversão
        chain = user_request.chain.upper()
        from_token = extracted_data.get("fromToken", "").upper()
        to_token = extracted_data.get("toToken", "").upper()
        from_token_decimals = TOKEN_INFO.get(chain, {}).get(from_token, {}).get("decimals", 6)
        to_token_decimals = TOKEN_INFO.get(chain, {}).get(to_token, {}).get("decimals", 6)
        quote = convert_quote_to_human_readable(quote, from_token_decimals, to_token_decimals)
        quote = filter_quote_fields(quote)
        return quote
