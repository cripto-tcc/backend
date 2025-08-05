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
            "Se a intenção for cotação ou swap, extraia também os campos fromToken, toToken e fromAmount do input, e responda SOMENTE neste formato JSON:\n"
            '{\"intent\": \"cotacao\", \"fromToken\": \"BTC\", \"toToken\": \"USDC\", \"fromAmount\": \"10\"}\n'
            '{\"intent\": \"swap\", \"fromToken\": \"BTC\", \"toToken\": \"USDC\", \"fromAmount\": \"10\"}\n'
            "IMPORTANTE: \n"
            "- fromToken: é o token que o usuário QUER TROCAR (o que ele TEM)\n"
            "- toToken: é o token que o usuário QUER RECEBER\n"
            "- fromAmount: é a quantidade do fromToken\n"
            "- intent: 'cotacao' para apenas ver preços, 'swap' para executar a troca\n"
            "- Para nomes de tokens, aceite variações como: 'Bitcoin' -> 'BTC', 'Ethereum' -> 'ETH', 'Tether' -> 'USDT', etc.\n"
            "- Se notar que o usuário errou o nome do token, tente corrigir para o nome correto!\n"
            "\n"
            "Exemplos:\n"
            "- 'quero trocar 1 BTC por USDC' -> intent: 'swap', fromToken: 'BTC', toToken: 'USDC', fromAmount: '1'\n"
            "- 'fazer swap de 1 Bitcoin para USD Coin' -> intent: 'swap', fromToken: 'Bitcoin', toToken: 'USD Coin', fromAmount: '1'\n"
            "- 'trocar 2 Ethereum por Tether' -> intent: 'swap', fromToken: 'Ethereum', toToken: 'Tether', fromAmount: '2'\n"
            "- 'qual a cotação de 1 WBTC em USDC' -> intent: 'cotacao', fromToken: 'WBTC', toToken: 'USDC', fromAmount: '1'\n"
            "- 'quanto vale 1 ETH em USDT' -> intent: 'cotacao', fromToken: 'ETH', toToken: 'USDT', fromAmount: '1'\n"
            "- 'cotação de 5 Polygon em Dai' -> intent: 'cotacao', fromToken: 'Polygon', toToken: 'Dai', fromAmount: '5'\n"
            "- 'quantos ETH vou ter se trocar 1000 USDC?' -> intent: 'cotacao', fromToken: 'USDC', toToken: 'ETH', fromAmount: '1000'\n"
            "- 'quantos link vou ter se trocar por 1000 dolar?' -> intent: 'cotacao', fromToken: 'dolar', toToken: 'link', fromAmount: '1000'\n"
            "- 'quero transferir 4 USDC para o endereço 0x6E5e81075873EA1f3fE04ae663111cB47B1c6bCD' -> intent: 'transferencia', token: 'USDC', amount: '4', toAddress: '0x6E5e81075873EA1f3fE04ae663111cB47B1c6bCD'\n"
            "- 'mandar 10 Ethereum para 0x1234567890123456789012345678901234567890' -> intent: 'transferencia', token: 'Ethereum', amount: '10', toAddress: '0x1234567890123456789012345678901234567890'\n"
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

    async def generate_friendly_message(self, quote_response):
        print("Quote response recebido:", quote_response)
        prompt = (
            "Receba o seguinte JSON de cotação de troca de tokens e gere uma mensagem amigável, clara e objetiva explicando para o usuário o resultado da cotação.\n"
            "\n"
            "# Instruções obrigatórias:\n"
            "- Informe quanto o usuário vai enviar (valor + símbolo do token de origem), usando o campo `fromAmount` ajustado pelas casas decimais do token de origem.\n"
            "- Informe quanto o usuário vai receber aproximadamente (valor + símbolo do token de destino), usando o campo `toAmount` ajustado pelas casas decimais do token de destino.\n"
            "- Use os campos `fromToken` e `toToken` da resposta para identificar os símbolos corretos dos tokens.\n"
            "- Sempre exiba a taxa estimada de rede, usando o valor em **USD** (campo `amountUSD` dentro de `gasCosts`) e o símbolo do token que paga a taxa (campo `symbol`, por ex. ETH). Formatação esperada:\n"
            "  Taxas estimadas da rede: ~$5,65 em ETH\n"
            "- Informe o tempo estimado de execução em segundos (campo `executionDuration`). Exemplo: Tempo de execução: ~30 segundos\n"
            "- Utilize o padrão numérico brasileiro: ponto (.) para separar milhares e vírgula (,) para separador decimal (ex.: 1.234,56).\n"
            "- Finalize com a seguinte observação obrigatória, em itálico:\n"
            "  *Lembrando que isso são cotações. Quando for fazer a troca, se atente nos valores atualizados e reais da troca.*\n"
            "\n"
            "# Regras:\n"
            "- Não afirme que a troca foi realizada. É apenas uma cotação.\n"
            "- Não invente dados. Use apenas o que está presente no JSON.\n"
            "- Não converta valores para outras moedas que não estejam no JSON.\n"
            "- Não ofereça conselhos financeiros ou sugestões pessoais.\n"
            "- Seja direto, claro e sem floreios.\n"
            "- IMPORTANTE: Use ** para negrito e * para itálico, exatamente como mostrado nos exemplos.\n"
            "\n"
            "# Exemplo de estrutura que pode ser usada (não precisa ser idêntica sempre, mas mantenha o mesmo tipo de clareza):\n"
            "Com [fromAmount] [fromToken], você vai receber aproximadamente **[toAmount] [toToken]**.\n"
            "\n"
            "⛽ Taxas estimadas da rede: **~$5,65** em ETH\n"
            "🕝 Tempo de execução: ~30 segundos\n"
            "\n"
            "*Lembrando que isso são cotações. Quando for fazer a troca, se atente nos valores atualizados e reais da troca.*\n"
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

    async def generate_transfer_message(self, transfer_response):
        """
        Gera mensagem amigável para transferências, incluindo informações
        sobre a transação
        """
        prompt = (
            "Receba o seguinte JSON de dados de transferência de tokens e "
            "gere uma mensagem amigável e clara explicando para o usuário "
            "o que acontecerá na transação.\n"
            "\n"
            "# Instruções obrigatórias:\n"
            "- Informe que esta é uma transação de TRANSFERÊNCIA "
            "(envio de tokens)\n"
            "- Informe quanto o usuário vai enviar (valor + símbolo do "
            "token), usando o campo `fromAmount`\n"
            "- Informe para qual endereço será feita a transferência "
            "(campo `toAddress`)\n"
            "- Use o campo `fromToken` da resposta para identificar o "
            "símbolo correto do token\n"
            "- Sempre exiba a taxa estimada de rede, usando o valor em "
            "**USD** (campo `amountUSD` dentro de `gasCosts`) e o símbolo "
            "do token que paga a taxa (campo `symbol`, por ex. ETH). "
            "Formatação esperada:\n"
            "  Taxas estimadas da rede: ~$5,50 em ETH\n"
            "- Informe o tempo estimado de execução em segundos "
            "(campo `executionDuration`). Exemplo: Tempo de execução: "
            "~30 segundos\n"
            "- Utilize o padrão numérico brasileiro: ponto (.) para "
            "separar milhares e vírgula (,) para separador decimal "
            "(ex.: 1.234,56).\n"
            "- Finalize informando que o usuário poderá revisar e confirmar "
            "a transação na próxima etapa.\n"
            "\n"
            "# Regras:\n"
            "- Deixe claro que esta é uma transação real de transferência, "
            "não apenas uma simulação\n"
            "- Não invente dados. Use apenas o que está presente no JSON.\n"
            "- Não converta valores para outras moedas que não estejam no JSON.\n"
            "- Seja direto, claro e sem floreios.\n"
            "- IMPORTANTE: Use ** para negrito e * para itálico.\n"
            "- IMPORTANTE: Mostre apenas os primeiros 6 e últimos 4 "
            "caracteres do endereço de destino para segurança\n"
            "\n"
            "# Exemplo de estrutura:\n"
            "📤 **Processo de transferência de tokens iniciado!**\n"
            "\n"
            "Você estará enviando [fromAmount] [fromToken] para o endereço "
            "**0x1234...5678**.\n"
            "\n"
            "⛽ Taxas estimadas da rede: **~$5,50** em ETH\n"
            "🕝 Tempo de execução: ~30 segundos\n"
            "\n"
            "Na próxima etapa você poderá revisar todos os detalhes e "
            "confirmar a transação.\n"
            "\n"
            "Deseja continuar com a transferência?"
            f"JSON: {json.dumps(transfer_response, ensure_ascii=False)}"
        )

        print("\n\n !!!!!! Prompt enviado ao Gemini "
              "(generate_transfer_message)", "\n\n")

        # Gemini API uses generate_content for streaming as well
        response_stream = await self.model.generate_content_async(prompt, stream=True)

        async for chunk in response_stream:
            if chunk.text:  # Check if text is available in the chunk
                yield chunk.text

    async def generate_swap_message(self, swap_response):
        """
        Gera mensagem amigável para swaps, incluindo informações sobre a transação
        """
        prompt = (
            "Receba o seguinte JSON de dados de swap de tokens e gere uma mensagem amigável e clara explicando para o usuário o que acontecerá na transação.\n"
            "\n"
            "# Instruções obrigatórias:\n"
            "- Informe que esta é uma transação de SWAP (troca), não apenas uma cotação\n"
            "- Informe quanto o usuário vai enviar (valor + símbolo do token de origem), usando o campo `fromAmount` ajustado pelas casas decimais do token de origem.\n"
            "- Informe quanto o usuário vai receber aproximadamente (valor + símbolo do token de destino), usando o campo `toAmount` ajustado pelas casas decimais do token de destino.\n"
            "- Use os campos `fromToken` e `toToken` da resposta para identificar os símbolos corretos dos tokens.\n"
            "- Sempre exiba a taxa estimada de rede, usando o valor em **USD** (campo `amountUSD` dentro de `gasCosts`) e o símbolo do token que paga a taxa (campo `symbol`, por ex. ETH). Formatação esperada:\n"
            "  Taxas estimadas da rede: ~$5,65 em ETH\n"
            "- Informe o tempo estimado de execução em segundos (campo `executionDuration`). Exemplo: Tempo de execução: ~30 segundos\n"
            "- Utilize o padrão numérico brasileiro: ponto (.) para separar milhares e vírgula (,) para separador decimal (ex.: 1.234,56).\n"
            "- Finalize informando que o usuário poderá revisar e confirmar a transação na próxima etapa.\n"
            "\n"
            "# Regras:\n"
            "- Deixe claro que esta é uma transação real de swap, não apenas cotação\n"
            "- Não invente dados. Use apenas o que está presente no JSON.\n"
            "- Não converta valores para outras moedas que não estejam no JSON.\n"
            "- Seja direto, claro e sem floreios.\n"
            "- IMPORTANTE: Use ** para negrito e * para itálico.\n"
            "\n"
            "# Exemplo de estrutura:\n"
            "🔄 **Processo de troca entre tokens (Swap) iniciado!**\n"
            "\n"
            "Você estará trocando [fromAmount] [fromToken] por aproximadamente **[toAmount] [toToken]**.\n"
            "\n"
            "⛽ Taxas estimadas da rede: **~$5,65** em ETH\n"
            "🕝 Tempo de execução: ~30 segundos\n"
            "\n"
            "Na próxima etapa você poderá revisar todos os detalhes e confirmar a transação.\n"
            "\n"
            "Deseja continuar com a transação?"
            f"JSON: {json.dumps(swap_response, ensure_ascii=False)}"
        )

        print("\n\n !!!!!! Prompt enviado ao Gemini (generate_swap_message)", "\n\n")
        
        # Gemini API uses generate_content for streaming as well
        response_stream = await self.model.generate_content_async(prompt, stream=True)
        
        async for chunk in response_stream:
            if chunk.text: # Check if text is available in the chunk
                yield chunk.text
