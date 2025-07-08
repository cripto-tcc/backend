import httpx

# Dicionário global para armazenar os tokens de cada rede após integração com LI.FI
TOKEN_INFO = {}

import asyncio

async def fetch_and_store_tokens(chain_name):
    chain_name_upper = chain_name.upper()
    url = f"https://li.quest/v1/tokens?chains={chain_name}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        tokens_by_chain = data.get("tokens", {})
        # tokens_by_chain é um dict: {chainId: [tokens]}
        # Vamos armazenar por symbol para facilitar o acesso
        # Agora vamos lidar com tokens duplicados, mantendo o de maior valor
        tokens_dict = {}
        for chain_id, tokens in tokens_by_chain.items():
            # Primeiro, agrupamos todos os tokens pelo símbolo
            tokens_by_symbol = {}
            for token in tokens:
                symbol = token.get("symbol", "").upper()
                if symbol:
                    if symbol not in tokens_by_symbol:
                        tokens_by_symbol[symbol] = []
                    tokens_by_symbol[symbol].append(token)
            
            # Agora, para cada símbolo, selecionamos o token com maior valor
            for symbol, token_list in tokens_by_symbol.items():
                # Se houver mais de um token com o mesmo símbolo, mostramos um log
                #if len(token_list) > 1:
                    #print(f"Encontrados {len(token_list)} tokens com o símbolo {symbol}:")
                    #for t in token_list:
                        #print(f"  - {t.get('name')}: {t.get('priceUSD') or 0} USD (address: {t.get('address')})")
                
                # Ordenamos por priceUSD (do maior para o menor)
                # Tratamos None como 0 para evitar erros de comparação
                sorted_tokens = sorted(token_list, key=lambda t: float(t.get("priceUSD", 0) or 0), reverse=True)
                # Pegamos o primeiro (maior valor)
                best_token = sorted_tokens[0]
                
                if len(token_list) > 1:
                    print(f"Selecionado para {symbol}: {best_token.get('name')} com valor {best_token.get('priceUSD')} USD")
                
                tokens_dict[symbol] = {
                    "address": best_token.get("address"),
                    "decimals": best_token.get("decimals"),
                    "name": best_token.get("name"),
                    "priceUSD": best_token.get("priceUSD"),
                    "logoURI": best_token.get("logoURI"),
                    "chainId": best_token.get("chainId"),
                }
        TOKEN_INFO[chain_name_upper] = tokens_dict


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
        print(" \n ### URL da LI.FI:", url)
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            quote = response.json()
            
            quote['fromToken'] = from_token
            quote['toToken'] = to_token
            
            return quote
        
    async def get_swap_quote(self, user_request, extracted_data):
        """
        Obtém cotação de swap do LI.FI com dados de transação
        Similar ao get_quote, mas retorna dados completos para executar o swap
        """
        chain = user_request.chain.upper()
        # Usa os dados extraídos pelo Gemini
        from_token = extracted_data.get("fromToken", "").upper()
        to_token = extracted_data.get("toToken", "").upper()
        amount = extracted_data.get("fromAmount", "")
        print(f"Swap - Extraído: from_token={from_token}, to_token={to_token}, amount={amount}")

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
        print(" \n ### URL da LI.FI (Swap):", url)
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            swap_quote = response.json()
            
            # Adicionar informações de token para o frontend
            swap_quote['fromToken'] = from_token
            swap_quote['toToken'] = to_token
            
            # Retornar dados completos para o swap, incluindo transactionRequest
            return swap_quote