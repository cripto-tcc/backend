import httpx

# Mapeamento de tokens para Ethereum com endereço e decimais
TOKEN_INFO = {
    "ETH": {
        "WBTC": {
            "address": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
            "decimals": 8
        },
        "USDC": {
            "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "decimals": 6
        }
    }
}

def convert_quote_to_human_readable(quote, from_token_decimals, to_token_decimals):
    # Converte os principais campos numéricos do JSON para formato "humano"
    def convert(value, decimals):
        try:
            return float(value) / (10 ** decimals)
        except Exception:
            return value

    if 'fromAmount' in quote:
        quote['fromAmount'] = convert(quote['fromAmount'], from_token_decimals)
    if 'toAmount' in quote:
        quote['toAmount'] = convert(quote['toAmount'], to_token_decimals)
    if 'estimate' in quote:
        if 'fromAmount' in quote['estimate']:
            quote['estimate']['fromAmount'] = convert(quote['estimate']['fromAmount'], from_token_decimals)
        if 'toAmount' in quote['estimate']:
            quote['estimate']['toAmount'] = convert(quote['estimate']['toAmount'], to_token_decimals)
    return quote

class LifiService:
    async def get_quote(self, user_request, extracted_data):
        chain = user_request.chain.upper()
        # Usa os dados extraídos pelo ChatGPT
        from_token = extracted_data.get("fromToken", "").upper()
        to_token = extracted_data.get("toToken", "").upper()
        amount = extracted_data.get("fromAmount", "")
        print(f"Extraído: from_token={from_token}, to_token={to_token}, amount={amount}")

        # Obter info dos tokens
        from_token_info = TOKEN_INFO.get(chain, {}).get(from_token)
        to_token_info = TOKEN_INFO.get(chain, {}).get(to_token)
        if not from_token_info or not to_token_info:
            return {"error": "Token ou chain não suportado."}

        from_token_address = from_token_info["address"]
        to_token_address = to_token_info["address"]
        from_token_decimals = from_token_info["decimals"]
        to_token_decimals = to_token_info["decimals"]

        try:
            from_amount = str(int(float(amount) * (10 ** from_token_decimals)))
        except Exception:
            return {"error": "Valor de quantidade inválido."}

        url = (
            f"https://li.quest/v1/quote?fromChain={chain}"
            f"&toChain={chain}"
            f"&fromToken={from_token_address}"
            f"&toToken={to_token_address}"
            f"&fromAddress={user_request.walletAddress}"
            f"&fromAmount={from_amount}"
        )
        print("URL da LI.FI:", url)
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            quote = response.json()
            
            quote['fromToken'] = from_token
            quote['toToken'] = to_token
            
            return quote
