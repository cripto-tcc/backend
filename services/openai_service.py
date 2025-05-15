import os
import json
import openai

class OpenAIService:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def classify_intent_and_extract(self, user_input):
        prompt = (
            "Classifique a intenção do usuário a partir do input abaixo. "
            "Se a intenção for cotação, extraia também os campos fromToken, toToken e fromAmount do input, e responda SOMENTE neste formato JSON:\n"
            '{"intent": "cotacao", "fromToken": "BTC", "toToken": "USDC", "fromAmount": "10"}\n'
            "IMPORTANTE: \n"
            "- fromToken: é o token que o usuário QUER TROCAR (o que ele TEM)\n"
            "- toToken: é o token que o usuário QUER RECEBER\n"
            "- fromAmount: é a quantidade do fromToken\n"
            "\n"
            "Exemplos:\n"
            "- 'quero trocar 1 BTC por USDC' -> fromToken: 'BTC', toToken: 'USDC', fromAmount: '1'\n"
            "- 'qual a cotação de 1 WBTC em USDC' -> fromToken: 'WBTC', toToken: 'USDC', fromAmount: '1'\n"
            "- 'quanto vale 1 ETH em USDT' -> fromToken: 'ETH', toToken: 'USDT', fromAmount: '1'\n"
            "\n"
            "Se não for cotação, responda apenas com a intenção (swap ou transferencia).\n"
            f"Input: {user_input}"
        )
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um classificador de intenções e extrator de entidades para operações de cripto. Preste atenção na ordem dos tokens: fromToken é o que o usuário TEM, toToken é o que ele quer RECEBER."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0
        )
        content = response.choices[0].message.content.strip()
        print("Resposta bruta do ChatGPT (classify_intent_and_extract):", content)
        try:
            data = json.loads(content)
            print("Dados extraídos:", data)  # Log adicional
            return data
        except Exception:
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
            "Com 100 USDC, você vai receber aproximadamente **0,000973 WBTC**.\n"
            "\n"
            "⛽ Taxas estimadas da rede: **~$5,65** em ETH\n"
            "⏱ Tempo de execução: ~30 segundos\n"
            "\n"
            "*Lembrando que isso são cotações. Quando for fazer a troca, se atente nos valores atualizados e reais da troca.*\n"
            "\n"
            f"JSON: {json.dumps(quote_response, ensure_ascii=False)}"
        )

        print("\n\n ###Prompt enviado ao GPT (generate_friendly_message):", prompt, "\n\n")
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente que gera mensagens amigáveis para usuários de cripto. Use ** para negrito e * para itálico."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7,
            stream=True
        )
        
        buffer = ""
        async for chunk in response:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                buffer += content
                if "**" in buffer:
                    yield buffer
                    buffer = ""
                elif len(buffer) > 10:
                    yield buffer
                    buffer = ""
        
        if buffer:
            yield buffer
