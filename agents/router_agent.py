from services.gemini_service import GeminiService
from agents.quote_agent import QuoteAgent
from agents.swap_agent import SwapAgent
from agents.transfer_agent import TransferAgent


class RouterAgent:
    def __init__(self):
        self.gemini_service = GeminiService()
        self.quote_agent = QuoteAgent()
        self.swap_agent = SwapAgent()
        self.transfer_agent = TransferAgent()

    async def handle(self, user_request):
        try:
            result = await self.gemini_service.classify_intent_and_extract(user_request.input)
            intent = result.get("intent")
            language = result.get("language", "pt")  # Default para português

            if intent == "cotacao":
                quote = await self.quote_agent.get_quote(user_request, result)
                # Verifica se houve erro na cotação
                if "error" in quote:
                    # Usa o método existente com contexto específico
                    async for chunk in self.gemini_service.generate_error_response(language, f"Erro na cotação: {quote['error']}"):
                        yield chunk
                    return
                async for chunk in self.gemini_service.generate_friendly_message(quote, language):
                    yield chunk
            elif intent == "swap":
                swap_result = await self.swap_agent.get_swap(user_request, result)
                # Verifica se houve erro no swap
                if "error" in swap_result:
                    # Usa o método existente com contexto específico
                    async for chunk in self.gemini_service.generate_error_response(language, f"Erro no swap: {swap_result['error']}"):
                        yield chunk
                    return
                
                # Se for dados estruturados de swap, gera mensagem e retorna dados
                if swap_result.get("type") == "swap_data":
                    # Gera mensagem amigável
                    async for chunk in self.gemini_service.generate_swap_message(swap_result["data"], language):
                        yield chunk
                    # Retorna dados da transação
                    yield {
                        "type": "transaction",
                        "data": swap_result["data"]
                    }
                else:
                    # Fallback para dados antigos
                    async for chunk in self.gemini_service.generate_swap_message(
                        swap_result, language
                    ):
                        yield chunk
            elif intent == "transferencia":
                transfer_result = await self.transfer_agent.get_transfer(
                    user_request, result
                )
                # Verifica se houve erro na transferência
                if "error" in transfer_result:
                    # Usa o método existente com contexto específico
                    async for chunk in self.gemini_service.generate_error_response(language, f"Erro na transferência: {transfer_result['error']}"):
                        yield chunk
                    return

                # Se for dados estruturados de transferência, gera mensagem e retorna dados
                if transfer_result.get("type") == "transfer_data":
                    # Gera mensagem amigável
                    async for chunk in self.gemini_service.generate_transfer_message(
                        transfer_result["data"], language
                    ):
                        yield chunk
                    # Retorna dados da transação
                    yield {
                        "type": "transaction",
                        "data": transfer_result["data"]
                    }
                else:
                    # Fallback para dados antigos
                    async for chunk in self.gemini_service.generate_transfer_message(
                        transfer_result, language
                    ):
                        yield chunk
            else:
                # Para mensagens que não são das funcionalidades principais, 
                # gera uma resposta amigável e orientativa
                async for chunk in self.gemini_service.generate_helpful_response(user_request.input, language):
                    yield chunk
        except Exception as e:
            # Log do erro para debugging (sem exposição ao usuário)
            print(f"Erro interno no RouterAgent: {str(e)}")
            
            # Gera resposta amigável de erro para o usuário
            async for chunk in self.gemini_service.generate_error_response(language, f"Erro durante processamento: {type(e).__name__}"):
                yield chunk
