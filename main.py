from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from models.request_model import UserRequest
from agents.router_agent import RouterAgent
from services.supabase_service import supabase_service
from services.moralis_service import moralis_service
from dotenv import load_dotenv
import json
import os
import time

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv('CORS_ORIGIN')], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

router_agent = RouterAgent()

@app.post("/process")
async def process_request(request: Request):
    data = await request.json()
    user_request = UserRequest(**data)
    
    # Marca o início do processamento
    start_time = time.time()
    
    # Detecta o origin baseado no CORS origin
    origin = "production"  # Default
    if hasattr(request, 'headers'):
        origin_header = request.headers.get('origin', '')
        if 'localhost' in origin_header or '127.0.0.1' in origin_header:
            origin = "local"
    
    # Tracking do prompt (não bloqueia a resposta)
    message_id = await supabase_service.safe_insert_prompt(user_request.input, origin)
    
    response_content = ""
    
    async def generate():
        nonlocal response_content
        
        print(f"🔍 DEBUG: Processando prompt: '{user_request.input}'")
        print(f"🔍 DEBUG: Wallet: {user_request.walletAddress}, Chain: {user_request.chain}")
        
        # Processa a resposta principal (não depende do Supabase)
        try:
            async for chunk in router_agent.handle(user_request):
                print(f"🔍 DEBUG: Chunk recebido: {type(chunk)} - {chunk}")
                if isinstance(chunk, dict):
                    if chunk.get("type") == "transaction":
                        yield f"data: {json.dumps(chunk)}\n\n"
                    else:
                        yield f"data: {json.dumps(chunk)}\n\n"
                else:
                    response_content += chunk
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
        except Exception as e:
            print(f"❌ DEBUG: Erro no processamento: {e}")
            error_msg = f"Erro interno: {str(e)}"
            response_content += error_msg
            yield f"data: {json.dumps({'content': error_msg})}\n\n"
        
        # Retorna o ID da mensagem para o frontend
        if message_id:
            yield f"data: {json.dumps({'message_id': message_id, 'type': 'tracking'})}\n\n"
        
        yield "data: [DONE]\n\n"
        
        # Calcula o tempo de resposta
        end_time = time.time()
        response_time = round(end_time - start_time, 2)
        
        # Atualiza a mensagem existente com a resposta completa
        if message_id:
            try:
                await supabase_service.update_message(
                    message_id, 
                    response=response_content, 
                    response_time=response_time
                )
            except Exception as e:
                print(f"⚠️ Erro ao atualizar resposta no banco (não crítico): {e}")
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/track/{message_id}")
async def update_message_tracking(message_id: int, request: Request):
    """Atualiza qualquer propriedade de tracking de uma mensagem"""
    try:
        # Obtém os dados do body
        body = await request.json()
        
        # Atualiza a mensagem com os campos fornecidos
        result = await supabase_service.update_message(message_id, **body)
        
        return {
            "success": True,
            "message": "Mensagem atualizada com sucesso",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar mensagem: {str(e)}")

@app.post("/humanize-error")
async def humanize_error(request: Request):
    """Endpoint para humanizar erros de UI usando o Gemini"""
    try:
        data = await request.json()
        error_message = data.get("error_message", "")
        language = data.get("language", "pt")
        
        if not error_message:
            raise HTTPException(status_code=400, detail="Campo 'error_message' é obrigatório")
        
        async def generate_humanized_error():
            async for chunk in router_agent.gemini_service.generate_error_response(
                language=language, 
                error_context=f"Erro de interface/carteira: {error_message}"
            ):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield f"data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_humanized_error(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao humanizar erro: {str(e)}")

@app.post("/humanize-success")
async def humanize_success(request: Request):
    """Endpoint para gerar mensagens de sucesso amigáveis usando o Gemini"""
    try:
        data = await request.json()
        transaction_hash = data.get("transaction_hash", "")
        transaction_type = data.get("transaction_type", "transaction")
        language = data.get("language", "pt")
        
        if not transaction_hash:
            raise HTTPException(status_code=400, detail="Campo 'transaction_hash' é obrigatório")
        
        async def generate_success_message():
            async for chunk in router_agent.gemini_service.generate_success_message(
                transaction_hash=transaction_hash,
                transaction_type=transaction_type,
                language=language
            ):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield f"data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_success_message(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar mensagem de sucesso: {str(e)}")

@app.get("/test/messages")
async def test_get_messages():
    """Rota para verificar as mensagens salvas"""
    try:
        messages = await supabase_service.get_messages(limit=5)
        
        return {
            "success": True,
            "message": f"Encontradas {len(messages)} mensagens",
            "data": messages
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Erro ao buscar mensagens: {str(e)}"
        }

@app.get("/wallets/{wallet}/history")
async def get_wallet_history(
    wallet: str,
    chain: str = Query(..., description="Cadeia blockchain (ex: base, eth, polygon)"),
    limit: int = Query(5, description="Número máximo de transações a retornar")
):
    """
    Busca o histórico de transações de uma carteira via Moralis
    
    Args:
        wallet: Endereço da carteira (path parameter)
        chain: Cadeia blockchain (ex: base, eth, polygon) - query parameter obrigatório
        limit: Número máximo de transações a retornar (padrão: 5) - query parameter opcional
    
    Returns:
        dict: Resposta da API da Moralis
    """
    try:
        result = await moralis_service.get_wallet_history(wallet, chain, limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar histórico: {str(e)}")

@app.get("/wallets/{wallet}/tokens")
async def get_wallet_tokens(
    wallet: str,
    chain: str = Query(..., description="Cadeia blockchain (ex: base, eth, polygon)")
):
    """
    Busca os tokens de uma carteira via Moralis
    
    Args:
        wallet: Endereço da carteira (path parameter)
        chain: Cadeia blockchain (ex: base, eth, polygon) - query parameter obrigatório
    
    Returns:
        dict: Resposta da API da Moralis
    """
    try:
        result = await moralis_service.get_wallet_tokens(wallet, chain)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar tokens: {str(e)}")
