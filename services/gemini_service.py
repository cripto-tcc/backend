import os
import json
import google.generativeai as genai
from services.token_normalizer import TokenNormalizer


class GeminiService:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        # For text-only input
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    async def classify_intent_and_extract(self, user_input):
        prompt = (
            "Classifique a intenção do usuário a partir do input abaixo. "
            "Se a intenção for cotação ou swap, extraia também os campos fromToken, toToken e fromAmount do input. "
            "IMPORTANTE: Detecte também o idioma da mensagem do usuário e inclua no JSON de resposta. "
            "Responda SOMENTE neste formato JSON:\n"
            '{\"intent\": \"cotacao\", \"fromToken\": \"BTC\", \"toToken\": \"USDC\", \"fromAmount\": \"10\", \"language\": \"pt\"}\n'
            '{\"intent\": \"swap\", \"fromToken\": \"BTC\", \"toToken\": \"USDC\", \"fromAmount\": \"10\", \"language\": \"en\"}\n'
            "IMPORTANTE: \n"
            "- fromToken: é o token que o usuário QUER TROCAR (o que ele TEM)\n"
            "- toToken: é o token que o usuário QUER RECEBER\n"
            "- fromAmount: é a quantidade do fromToken\n"
            "- intent: 'cotacao' para apenas ver preços, 'swap' para executar a troca\n"
            "- language: código do idioma detectado ('pt' para português, 'en' para inglês, 'es' para espanhol, etc.)\n"
            "- Para nomes de tokens, aceite variações como: 'Bitcoin' -> 'BTC', 'Ethereum' -> 'ETH', 'Tether' -> 'USDT', etc.\n"
            "- Se notar que o usuário errou o nome do token, tente corrigir para o nome correto!\n"
            "\n"
            "Exemplos:\n"
            "- 'quero trocar 1 BTC por USDC' -> intent: 'swap', fromToken: 'BTC', toToken: 'USDC', fromAmount: '1', language: 'pt'\n"
            "- 'fazer swap de 1 Bitcoin para USD Coin' -> intent: 'swap', fromToken: 'Bitcoin', toToken: 'USD Coin', fromAmount: '1', language: 'pt'\n"
            "- 'I want to swap 2 Ethereum for Tether' -> intent: 'swap', fromToken: 'Ethereum', toToken: 'Tether', fromAmount: '2', language: 'en'\n"
            "- 'what is the quote for 1 WBTC in USDC' -> intent: 'cotacao', fromToken: 'WBTC', toToken: 'USDC', fromAmount: '1', language: 'en'\n"
            "- 'quanto vale 1 ETH em USDT' -> intent: 'cotacao', fromToken: 'ETH', toToken: 'USDT', fromAmount: '1', language: 'pt'\n"
            "- 'cotação de 5 Polygon em Dai' -> intent: 'cotacao', fromToken: 'Polygon', toToken: 'Dai', fromAmount: '5', language: 'pt'\n"
            "- 'how many ETH will I get if I swap 1000 USDC?' -> intent: 'cotacao', fromToken: 'USDC', toToken: 'ETH', fromAmount: '1000', language: 'en'\n"
            "- 'quantos link vou ter se trocar por 1000 dolar?' -> intent: 'cotacao', fromToken: 'dolar', toToken: 'link', fromAmount: '1000', language: 'pt'\n"
            "- 'quero transferir 4 USDC para o endereço 0x6E5e81075873EA1f3fE04ae663111cB47B1c6bCD' -> intent: 'transferencia', token: 'USDC', amount: '4', toAddress: '0x6E5e81075873EA1f3fE04ae663111cB47B1c6bCD', language: 'pt'\n"
            "- 'transfer 10 Ethereum to 0x1234567890123456789012345678901234567890' -> intent: 'transferencia', token: 'Ethereum', amount: '10', toAddress: '0x1234567890123456789012345678901234567890', language: 'en'\n"
            "\n"
            f"Input: {user_input}"
        )

        # Gemini API uses generate_content instead of chat.completions.create
        # The response structure is also different.
        response = await self.model.generate_content_async(prompt)

        content = response.text.strip()
        print("Resposta bruta do Gemini (classify_intent_and_extract):", content)
        try:
            # Attempt to remove markdown and parse JSON
            cleaned_content = content.replace('```json', '').replace('```', '').strip()
            data = json.loads(cleaned_content)
            print("Dados extraídos:", data)
            
            # Normaliza os tokens usando o TokenNormalizer
            normalized_data = TokenNormalizer.normalize_extracted_data(data)
            print("Dados após normalização:", normalized_data)
            return normalized_data
        except Exception as e:
            print(f"Erro ao fazer parse do JSON: {e}. Conteúdo: {content}")
            # Fallback if JSON parsing fails
            return {"intent": content.lower()}

    async def generate_friendly_message(self, quote_response, language="pt"):
        print("Quote response recebido:", quote_response)
        
        prompt = (
            f"Receba o seguinte JSON de cotação de troca de tokens e gere uma mensagem amigável, clara e objetiva explicando para o usuário o resultado da cotação. "
            f"IMPORTANTE: Responda no idioma detectado: {language}.\n"
            "\n"
            "# Instruções obrigatórias:\n"
            "- Informe quanto o usuário vai enviar (valor + símbolo do token de origem), usando o campo `fromAmount` ajustado pelas casas decimais do token de origem.\n"
            "- Informe quanto o usuário vai receber aproximadamente (valor + símbolo do token de destino), usando o campo `toAmount` ajustado pelas casas decimais do token de destino.\n"
            "- Use os campos `fromToken` e `toToken` da resposta para identificar os símbolos corretos dos tokens.\n"
            "- Sempre exiba a taxa estimada de rede, usando o valor em **USD** (campo `amountUSD` dentro de `gasCosts`) e o símbolo do token que paga a taxa (campo `symbol`, por ex. ETH).\n"
            "- Informe o tempo estimado de execução em segundos (campo `executionDuration`).\n"
            "- Use a formatação numérica apropriada para o idioma (ex: português/espanhol usam vírgula para decimal, inglês usa ponto).\n"
            "- Finalize com uma observação sobre serem cotações e atenção aos valores reais na troca.\n"
            "\n"
            "# Regras:\n"
            "- Não afirme que a troca foi realizada. É apenas uma cotação.\n"
            "- Não invente dados. Use apenas o que está presente no JSON.\n"
            "- Não converta valores para outras moedas que não estejam no JSON.\n"
            "- Não ofereça conselhos financeiros ou sugestões pessoais.\n"
            "- Seja direto, claro e sem floreios.\n"
            "- IMPORTANTE: Use ** para negrito e * para itálico.\n"
            "\n"
            "# Exemplo de estrutura (adapte ao idioma solicitado):\n"
            "Com [fromAmount] [fromToken], você vai receber aproximadamente **[toAmount] [toToken]**.\n"
            "\n"
            "⛽ Taxas estimadas da rede: **~$X,XX** em [symbol]\n"
            "🕝 Tempo de execução: ~X segundos\n"
            "\n"
            "*Observação sobre cotações vs valores reais da troca.*\n"
            "\n"
            f"JSON: {json.dumps(quote_response, ensure_ascii=False)}"
        )

        print("\n\n !!!!!! Prompt enviado ao Gemini (generate_friendly_message):", prompt, "\n\n")
        
        # Gemini API uses generate_content for streaming as well
        # The response structure for streaming chunks is different.
        response_stream = await self.model.generate_content_async(prompt, stream=True)
        
        async for chunk in response_stream:
            if chunk.text:  # Check if text is available in the chunk
                yield chunk.text

    async def generate_transfer_message(self, transfer_response, language="pt"):
        """
        Gera mensagem amigável para transferências, incluindo informações
        sobre a transação
        """
        prompt = (
            f"Receba o seguinte JSON de dados de transferência de tokens e gere uma mensagem amigável e clara explicando para o usuário o que acontecerá na transação. "
            f"IMPORTANTE: Responda no idioma detectado: {language}.\n"
            "\n"
            "# Instruções obrigatórias:\n"
            "- Informe que esta é uma transação de TRANSFERÊNCIA (envio de tokens)\n"
            "- Informe quanto o usuário vai enviar (valor + símbolo do token), usando o campo `fromAmount`\n"
            "- Informe para qual endereço será feita a transferência (campo `toAddress`)\n"
            "- Use o campo `fromToken` da resposta para identificar o símbolo correto do token\n"
            "- Sempre exiba a taxa estimada de rede, usando o valor em **USD** (campo `amountUSD` dentro de `gasCosts`) e o símbolo do token que paga a taxa (campo `symbol`, por ex. ETH)\n"
            "- Informe o tempo estimado de execução em segundos (campo `executionDuration`)\n"
            "- Use a formatação numérica apropriada para o idioma\n"
            "- Finalize informando que o usuário poderá revisar e confirmar a transação na próxima etapa\n"
            "- IMPORTANTE: Mostre apenas os primeiros 6 e últimos 4 caracteres do endereço de destino para segurança\n"
            "\n"
            "# Regras:\n"
            "- Deixe claro que esta é uma transação real de transferência, não apenas uma simulação\n"
            "- Não invente dados. Use apenas o que está presente no JSON.\n"
            "- Não converta valores para outras moedas que não estejam no JSON.\n"
            "- Seja direto, claro e sem floreios.\n"
            "- IMPORTANTE: Use ** para negrito e * para itálico.\n"
            "\n"
            "# Exemplo de estrutura (adapte ao idioma solicitado):\n"
            "📤 **Processo de transferência de tokens iniciado!**\n"
            "\n"
            "Você estará enviando [fromAmount] [fromToken] para o endereço **0x1234...5678**.\n"
            "\n"
            "⛽ Taxas estimadas da rede: **~$X,XX** em [symbol]\n"
            "🕝 Tempo de execução: ~X segundos\n"
            "\n"
            "Na próxima etapa você poderá revisar todos os detalhes e confirmar a transação.\n"
            "\n"
            "Deseja continuar com a transferência?\n"
            "\n"
            f"JSON: {json.dumps(transfer_response, ensure_ascii=False)}"
        )

        print("\n\n !!!!!! Prompt enviado ao Gemini "
              "(generate_transfer_message)", "\n\n")

        # Gemini API uses generate_content for streaming as well
        response_stream = await self.model.generate_content_async(prompt, stream=True)

        async for chunk in response_stream:
            if chunk.text:  # Check if text is available in the chunk
                yield chunk.text

    async def generate_swap_message(self, swap_response, language="pt"):
        """
        Gera mensagem amigável para swaps, incluindo informações sobre a transação
        """
        prompt = (
            f"Receba o seguinte JSON de dados de swap de tokens e gere uma mensagem amigável e clara explicando para o usuário o que acontecerá na transação. "
            f"IMPORTANTE: Responda no idioma detectado: {language}.\n"
            "\n"
            "# Instruções obrigatórias:\n"
            "- Informe que esta é uma transação de SWAP (troca), não apenas uma cotação\n"
            "- Informe quanto o usuário vai enviar (valor + símbolo do token de origem), usando o campo `fromAmount` ajustado pelas casas decimais do token de origem\n"
            "- Informe quanto o usuário vai receber aproximadamente (valor + símbolo do token de destino), usando o campo `toAmount` ajustado pelas casas decimais do token de destino\n"
            "- Use os campos `fromToken` e `toToken` da resposta para identificar os símbolos corretos dos tokens\n"
            "- Sempre exiba a taxa estimada de rede, usando o valor em **USD** (campo `amountUSD` dentro de `gasCosts`) e o símbolo do token que paga a taxa (campo `symbol`, por ex. ETH)\n"
            "- Informe o tempo estimado de execução em segundos (campo `executionDuration`)\n"
            "- Use a formatação numérica apropriada para o idioma\n"
            "- Finalize informando que o usuário poderá revisar e confirmar a transação na próxima etapa\n"
            "\n"
            "# Regras:\n"
            "- Deixe claro que esta é uma transação real de swap, não apenas cotação\n"
            "- Não invente dados. Use apenas o que está presente no JSON.\n"
            "- Não converta valores para outras moedas que não estejam no JSON.\n"
            "- Seja direto, claro e sem floreios.\n"
            "- IMPORTANTE: Use ** para negrito e * para itálico.\n"
            "\n"
            "# Exemplo de estrutura (adapte ao idioma solicitado):\n"
            "🔄 **Processo de troca entre tokens (Swap) iniciado!**\n"
            "\n"
            "Você estará trocando [fromAmount] [fromToken] por aproximadamente **[toAmount] [toToken]**.\n"
            "\n"
            "⛽ Taxas estimadas da rede: **~$X,XX** em [symbol]\n"
            "🕝 Tempo de execução: ~X segundos\n"
            "\n"
            "Na próxima etapa você poderá revisar todos os detalhes e confirmar a transação.\n"
            "\n"
            "Deseja continuar com a transação?\n"
            "\n"
            f"JSON: {json.dumps(swap_response, ensure_ascii=False)}"
        )

        print("\n\n !!!!!! Prompt enviado ao Gemini (generate_swap_message)", "\n\n")
        
        # Gemini API uses generate_content for streaming as well
        response_stream = await self.model.generate_content_async(prompt, stream=True)
        
        async for chunk in response_stream:
            if chunk.text: # Check if text is available in the chunk
                yield chunk.text

    async def generate_helpful_response(self, user_input, language="pt"):
        """
        Gera uma resposta amigável e orientativa para mensagens que não são das funcionalidades principais
        """
        prompt = (
            f"O usuário enviou a seguinte mensagem: '{user_input}'. "
            f"Esta mensagem não corresponde às funcionalidades principais da plataforma (cotações, swaps ou transferências de tokens). "
            f"IMPORTANTE: Responda no idioma detectado: {language}.\n"
            "\n"
            "# Seu papel:\n"
            "Você é um assistente especializado em operações blockchain que ajuda usuários com:\n"
            "- 📊 **Cotações de tokens** - Ver preços atuais de troca entre diferentes criptomoedas\n"
            "- 🔄 **Swaps de tokens** - Trocar uma criptomoeda por outra\n"
            "- 📤 **Transferências** - Enviar tokens para outros endereços\n"
            "\n"
            "# Instruções:\n"
            "- Responda de forma amigável e acolhedora à mensagem do usuário\n"
            "- Se for uma saudação (oi, olá, hello, etc.), cumprimente de volta\n"
            "- Se for uma pergunta geral, responda brevemente de forma educada\n"
            "- SEMPRE apresente as funcionalidades disponíveis de forma atrativa\n"
            "- Dê exemplos práticos de como usar cada funcionalidade\n"
            "- Use emojis para tornar a resposta mais visual e amigável\n"
            "- Seja conciso mas informativo\n"
            "- Encoraje o usuário a experimentar as funcionalidades\n"
            "- Na hora de apresentar exemplos, se limite a usar exemplos de tokens disponiveis nas redes ETH, Base e Polygon\n"
            "- Não forneça conselhos financeiros em nenhuma situação\n"
            "\n"
            "# Exemplos de como apresentar as funcionalidades:\n"
            "**Para cotações:** \"Quer saber quanto vale 1 BTC em USDC?\"\n"
            "**Para swaps:** \"Precisa trocar ETH por USDT?\"\n"
            "**Para transferências:** \"Quer enviar tokens para outro endereço?\"\n"
            "\n"
            "# Estrutura sugerida:\n"
            "1. Responda à mensagem do usuário de forma apropriada\n"
            "2. Apresente as funcionalidades disponíveis com exemplos\n"
            "3. Convide o usuário a experimentar\n"
            "\n"
            "Responda de forma natural e conversacional!"
        )

        print(f"\n\n !!!!!! Prompt enviado ao Gemini (generate_helpful_response) para input: '{user_input}'\n\n")
        
        # Gemini API uses generate_content for streaming as well
        response_stream = await self.model.generate_content_async(prompt, stream=True)
        
        async for chunk in response_stream:
            if chunk.text: # Check if text is available in the chunk
                yield chunk.text

    async def generate_error_response(self, language="pt", error_context=None):
        """
        Gera uma resposta amigável para situações de erro interno do sistema
        """
        prompt = (
            f"Ocorreu um erro interno no sistema enquanto o usuário tentava usar a plataforma de operações blockchain. "
            f"IMPORTANTE: Responda no idioma detectado: {language}.\n"
            "\n"
            "# Contexto do erro:\n"
            f"- {error_context if error_context else 'Erro interno não especificado'}\n"
            "\n"
            "# Seu papel:\n"
            "Você é um assistente especializado em operações blockchain. Precisa informar ao usuário sobre o problema de forma amigável e reconfortante.\n"
            "\n"
            "# Instruções:\n"
            "- Seja empático e compreensivo\n"
            "- Peça desculpas pelo inconveniente de forma genuína\n"
            "- Explique brevemente que houve um problema técnico temporário\n"
            "- Assegure que a equipe está trabalhando para resolver\n"
            "- Sugira que o usuário tente novamente em alguns minutos\n"
            "- Ofereça alternativas ou próximos passos\n"
            "- Use emojis para tornar a mensagem mais humana (mas sem exagerar)\n"
            "- Mantenha um tom profissional mas caloroso\n"
            "- NÃO mencione detalhes técnicos do erro\n"
            "- Termine de forma positiva e encorajadora\n"
            "\n"
            "# Elementos que DEVE incluir:\n"
            "- Pedido sincero de desculpas\n"
            "- Explicação simples do problema\n"
            "- Orientação sobre o que fazer\n"
            "- Reafirmação de que você está aqui para ajudar\n"
            "\n"
            "# Exemplo de estrutura (adapte ao idioma):\n"
            "🤖 Ops! Peço desculpas, mas algo não funcionou como esperado do nosso lado...\n"
            "\n"
            "Tivemos um probleminha técnico temporário que impediu o processamento da sua solicitação. Nossa equipe já está ciente e trabalhando na correção.\n"
            "\n"
            "💡 **O que você pode fazer:**\n"
            "- Tente novamente em alguns minutinhos\n"
            "- Se o problema persistir, verifique sua conexão\n"
            "- Estou aqui para ajudar com qualquer dúvida\n"
            "\n"
            "Obrigado pela paciência! 🙏\n"
            "\n"
            "Responda de forma natural, calorosa e profissional!"
        )

        print(f"\n\n !!!!!! Prompt enviado ao Gemini (generate_error_response) para idioma: '{language}'\n\n")
        
        # Gemini API uses generate_content for streaming as well
        response_stream = await self.model.generate_content_async(prompt, stream=True)
        
        async for chunk in response_stream:
            if chunk.text: # Check if text is available in the chunk
                yield chunk.text
