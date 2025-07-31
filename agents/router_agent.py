from services.gemini_service import GeminiService
from agents.quote_agent import QuoteAgent
from agents.swap_agent import SwapAgent

class RouterAgent:
    def __init__(self):
        self.gemini_service = GeminiService()
        self.quote_agent = QuoteAgent()
        self.swap_agent = SwapAgent()

    async def handle(self, user_request):
        try:
            result = await self.gemini_service.classify_intent_and_extract(user_request.input)
            intent = result.get("intent")
            
            if intent == "cotacao":
                quote = await self.quote_agent.get_quote(user_request, result)
                # Verifica se houve erro na cotação
                if "error" in quote:
                    yield f"❌ Erro: {quote['error']}"
                    return
                async for chunk in self.gemini_service.generate_friendly_message(quote):
                    yield chunk
            elif intent == "swap":
                swap_result = await self.swap_agent.get_swap(user_request, result)
                # Verifica se houve erro no swap
                if "error" in swap_result:
                    yield f"❌ Erro: {swap_result['error']}"
                    return
                
                # Se for dados estruturados de swap, gera mensagem e retorna dados
                if swap_result.get("type") == "swap_data":
                    # Gera mensagem amigável
                    async for chunk in self.gemini_service.generate_swap_message(swap_result["data"]):
                        yield chunk
                    # Retorna dados da transação
                    yield {
                        "type": "transaction",
                        "data": swap_result["data"]
                    }
                else:
                    # Fallback para dados antigos
                    async for chunk in self.gemini_service.generate_swap_message(swap_result):
                        yield chunk
            else:
                yield "Intenção não suportada no momento."
        except Exception as e:
            yield f"❌ Erro interno do servidor. Tente novamente."
