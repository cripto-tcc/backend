from services.openai_service import OpenAIService
from agents.quote_agent import QuoteAgent

class RouterAgent:
    def __init__(self):
        self.openai_service = OpenAIService()
        self.quote_agent = QuoteAgent()

    async def handle(self, user_request):
        result = await self.openai_service.classify_intent_and_extract(user_request.input)
        print("Resultado da classificação e extração:", result)
        intent = result.get("intent")
        if intent == "cotacao":
            # Passa os dados extraídos para o agente de cotação
            quote = await self.quote_agent.get_quote(user_request, result)
            friendly_message = await self.openai_service.generate_friendly_message(quote)
            return friendly_message
        else:
            return "Intenção não suportada no momento."
