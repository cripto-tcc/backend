import httpx

# Dicionário global para armazenar os tokens de cada rede após integração com LI.FI
TOKEN_INFO = {}

# Mapeamento de chain names para chain IDs
CHAIN_ID_MAPPING = {
    "ETH": "0x1",      # Ethereum Mainnet
    "BAS": "0x2105",  # Base
    "POL": "0x89"      # Polygon
}

import asyncio

async def fetch_and_store_tokens(chain_name):
    try:
        # Validação do parâmetro de entrada
        if not chain_name or not isinstance(chain_name, str):
            print(f"Erro: chain_name inválido: {chain_name}")
            return {"error": "chain_name deve ser uma string válida"}
        
        chain_name_upper = chain_name.upper()
        url = f"https://li.quest/v1/tokens?chains={chain_name}"
        
        print(f"Fazendo requisição para: {url}")
        
        # verify=False desabilita a verificação SSL para resolver problemas de certificado
        # Em produção, considere usar: verify="/path/to/certificate" ou configurar o sistema
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url)
            
            # Verificar status da resposta
            if response.status_code != 200:
                print(f"Erro na API: Status {response.status_code}")
                return {"error": f"Erro na API LI.FI: Status {response.status_code}"}
            
            data = response.json()
            
            if not data:
                print("Resposta vazia da API")
                return {"error": "Resposta vazia da API LI.FI"}
            
            tokens_by_chain = data.get("tokens", {})
            
            if not tokens_by_chain:
                print(f"Nenhum token encontrado para a chain: {chain_name}")
                return {"error": f"Nenhum token encontrado para a chain: {chain_name}"}
            
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
            
                    
                    tokens_dict[symbol] = {
                        "address": best_token.get("address"),
                        "decimals": best_token.get("decimals"),
                        "name": best_token.get("name"),
                        "priceUSD": best_token.get("priceUSD"),
                        "logoURI": best_token.get("logoURI"),
                        "chainId": best_token.get("chainId"),
                    }
            
            TOKEN_INFO[chain_name_upper] = tokens_dict
            print(f"Tokens armazenados com sucesso para {chain_name_upper}: {len(tokens_dict)} tokens")
            return {"success": True, "tokens_count": len(tokens_dict)}
            
    except Exception as e:
        print(f"Erro ao processar resposta da API LI.FI: {e}")
        return {"error": f"Erro ao processar resposta da API LI.FI: {str(e)}"}


async def get_gas_price(chain_name):
    """
    Busca o gas price atual da rede usando a API do LI.FI
    """
    chain_id = CHAIN_ID_MAPPING.get(chain_name.upper())
    if not chain_id:
        return {"error": f"Chain {chain_name} não suportada para gas price"}
    
    url = f"https://li.quest/v1/gas/prices/{chain_id}"
    
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url)
            
            if response.status_code != 200:
                return {"error": f"Erro ao buscar gas price (Status: {response.status_code})"}
            
            gas_data = response.json()
            
            # A API retorna o gas price diretamente como número
            if "standard" in gas_data:
                # Converte para hexadecimal
                gas_price_hex = hex(gas_data["standard"])
                return {"gasPrice": gas_price_hex}
            else:
                return {"error": "Dados de gas price não encontrados na resposta"}
                
    except Exception as e:
        return {"error": f"Erro ao buscar gas price: {str(e)}"}


def convert_quote_to_human_readable(quote, from_token_decimals, to_token_decimals):
    # Converte os principais campos numéricos do JSON para formato "humano"
    def convert(value, decimals):
        try:
            return float(value) / (10 ** decimals)
        except Exception:
            return value

    # Converte valores no nível raiz (se existirem)
    if 'fromAmount' in quote:
        quote['fromAmount'] = convert(quote['fromAmount'], from_token_decimals)
    if 'toAmount' in quote:
        quote['toAmount'] = convert(quote['toAmount'], to_token_decimals)
    
    # Converte valores dentro de 'estimate' e copia para o nível raiz
    if 'estimate' in quote and isinstance(quote['estimate'], dict):
        estimate = quote['estimate']
        
        # Converte valores dentro de estimate
        if 'fromAmount' in estimate:
            converted_from = convert(estimate['fromAmount'], from_token_decimals)
            estimate['fromAmount'] = converted_from
            # Adiciona no nível raiz para o Gemini usar
            quote['fromAmount'] = converted_from
            
        if 'toAmount' in estimate:
            converted_to = convert(estimate['toAmount'], to_token_decimals)
            estimate['toAmount'] = converted_to
            # Adiciona no nível raiz para o Gemini usar
            quote['toAmount'] = converted_to
            
        if 'toAmountMin' in estimate:
            estimate['toAmountMin'] = convert(estimate['toAmountMin'], to_token_decimals)

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
        
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url)
                
                # Verifica se a requisição foi bem-sucedida
                if response.status_code != 200:
                    print(f" DEBUG: Erro na API LI.FI - Status: {response.status_code}")
                    return {"error": f"Erro na API LI.FI (Status: {response.status_code})"}
                
                quote = response.json()
                
                # Verifica se a resposta contém erro
                if "error" in quote:
                    print(f"🔍 DEBUG: Erro na resposta LI.FI: {quote['error']}")
                    return {"error": f"Erro na cotação: {quote['error']}"}
                
                quote['fromToken'] = from_token
                quote['toToken'] = to_token
                
                return quote
                
        except httpx.RequestError as e:
            print(f"🔍 DEBUG: Erro de conexão com LI.FI: {e}")
            return {"error": "Erro de conexão com o serviço de cotação. Tente novamente."}
        except Exception as e:
            print(f"🔍 DEBUG: Erro inesperado na cotação: {e}")
            return {"error": "Erro inesperado na cotação. Tente novamente."}
        
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
            f"&slippage=0.01"
        )
        print(" \n ### URL da LI.FI (Swap):", url)
        
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url)
                
                # Verifica se a requisição foi bem-sucedida
                if response.status_code != 200:
                    print(f"🔍 DEBUG: Erro na API LI.FI (Swap) - Status: {response.status_code}")
                    return {"error": f"Erro na API LI.FI (Status: {response.status_code})"}
                
                swap_quote = response.json()
                
                # Verifica se a resposta contém erro
                if "error" in swap_quote:
                    print(f"🔍 DEBUG: Erro na resposta LI.FI (Swap): {swap_quote['error']}")
                    return {"error": f"Erro na cotação de swap: {swap_quote['error']}"}
                
                # Adicionar informações de token para o frontend
                swap_quote['fromToken'] = from_token
                swap_quote['toToken'] = to_token
                
                # Retornar dados completos para o swap, incluindo transactionRequest
                return swap_quote
                
        except httpx.RequestError as e:
            print(f"🔍 DEBUG: Erro de conexão com LI.FI (Swap): {e}")
            return {"error": "Erro de conexão com o serviço de cotação. Tente novamente."}
        except Exception as e:
            print(f"🔍 DEBUG: Erro inesperado na cotação de swap: {e}")
            return {"error": "Erro inesperado na cotação de swap. Tente novamente."}