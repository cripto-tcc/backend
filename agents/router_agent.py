from services.gemini_service import GeminiService
from agents.quote_agent import QuoteAgent
from agents.swap_agent import SwapAgent

class RouterAgent:
    def __init__(self):
        self.gemini_service = GeminiService()
        self.quote_agent = QuoteAgent()
        self.swap_agent = SwapAgent()

    async def handle(self, user_request):
        result = await self.gemini_service.classify_intent_and_extract(user_request.input)
        print("Resultado da classificação e extração:", result)
        intent = result.get("intent")
        
        if intent == "cotacao":
            quote = await self.quote_agent.get_quote(user_request, result)
            async for chunk in self.gemini_service.generate_friendly_message(quote):
                yield chunk
        elif intent == "swap":
            swap_data = await self.swap_agent.get_swap(user_request, result)
            async for chunk in self.gemini_service.generate_swap_message(swap_data):
                yield chunk
        else:
            yield "Intenção não suportada no momento."
