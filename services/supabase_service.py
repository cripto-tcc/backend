from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

class SupabaseService:
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_ANON_KEY')
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL e SUPABASE_ANON_KEY devem estar definidas no arquivo .env")
        
        self.client: Client = create_client(self.url, self.key)
    
    def get_client(self) -> Client:
        """Retorna o cliente do Supabase"""
        return self.client
    
    async def insert_message(self, prompt: str, response: str, response_time: float = None, 
                           action_clicked: bool = None, action_successful: bool = None, 
                           right_purpose: bool = None, right_values: bool = None, 
                           error_message: str = None, origin: str = None):
        """
        Insere uma nova mensagem na tabela messages
        
        Args:
            prompt: Texto do prompt
            response: Texto da resposta
            response_time: Tempo de resposta em segundos (opcional)
            action_clicked: Se a ação foi clicada (opcional)
            action_successful: Se a ação foi bem-sucedida (opcional)
            right_purpose: Se o propósito está correto (opcional)
            right_values: Se os valores estão corretos (opcional)
            error_message: Mensagem de erro (opcional)
            origin: Origem da mensagem - local/production (opcional)
        
        Returns:
            dict: Dados da mensagem inserida
        """
        try:
            data = {
                "prompt": prompt,
                "response": response
            }
            
            # Adiciona campos opcionais apenas se fornecidos
            if response_time is not None:
                data["response_time"] = response_time
            if action_clicked is not None:
                data["action_clicked"] = action_clicked
            if action_successful is not None:
                data["action_successful"] = action_successful
            if right_purpose is not None:
                data["right_purpose"] = right_purpose
            if right_values is not None:
                data["right_values"] = right_values
            if error_message is not None:
                data["error_message"] = error_message
            if origin is not None:
                data["origin"] = origin
            
            result = self.client.table("messages").insert(data).execute()
            
            if result.data:
                return result.data[0]
            else:
                raise Exception("Falha ao inserir dados na tabela messages")
                
        except Exception as e:
            raise Exception(f"Erro ao inserir mensagem: {str(e)}")
    
    async def get_messages(self, limit: int = 10):
        """
        Busca mensagens da tabela messages
        
        Args:
            limit: Número máximo de mensagens a retornar
        
        Returns:
            list: Lista de mensagens
        """
        try:
            result = self.client.table("messages").select("*").order("created_at", desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            raise Exception(f"Erro ao buscar mensagens: {str(e)}")
    
    async def safe_insert_prompt(self, prompt: str, origin: str = None):
        """Insere o prompt de forma segura, sem afetar a resposta principal"""
        try:
            result = await self.insert_message(
                prompt=prompt,
                response="",
                origin=origin
            )
            return result.get('id') if result else None
        except Exception as e:
            print(f"⚠️ Erro ao inserir prompt no banco (não crítico): {e}")
            return None
    
    async def update_action_clicked(self, message_id: int, clicked: bool = True):
        """Atualiza o status de action_clicked de uma mensagem"""
        try:
            result = self.client.table("messages").update({
                "action_clicked": clicked
            }).eq("id", message_id).execute()
            
            if result.data:
                return result.data[0]
            else:
                raise Exception("Mensagem não encontrada")
                
        except Exception as e:
            raise Exception(f"Erro ao atualizar action_clicked: {str(e)}")
    
    async def update_message(self, message_id: int, **kwargs):
        """Atualiza qualquer propriedade de uma mensagem"""
        try:
            # Filtra apenas campos válidos da tabela
            valid_fields = {
                'response', 'action_clicked', 'action_successful', 'right_purpose', 
                'right_values', 'error_message', 'response_time'
            }
            
            update_data = {}
            for key, value in kwargs.items():
                if key in valid_fields:
                    update_data[key] = value
            
            if not update_data:
                raise Exception("Nenhum campo válido fornecido para atualização")
            
            result = self.client.table("messages").update(update_data).eq("id", message_id).execute()
            
            if result.data:
                return result.data[0]
            else:
                raise Exception("Mensagem não encontrada")
                
        except Exception as e:
            raise Exception(f"Erro ao atualizar mensagem: {str(e)}")

# Instância global do serviço
supabase_service = SupabaseService()
