import httpx
import os
from dotenv import load_dotenv

load_dotenv()

class MoralisService:
    def __init__(self):
        self.api_key = os.getenv('MORALIS_API_KEY')
        self.base_url = "https://deep-index.moralis.io/api/v2.2"
        
        if not self.api_key:
            raise ValueError("MORALIS_API_KEY deve estar definida no arquivo .env")
        
        self.headers = {
            "accept": "application/json",
            "x-api-key": self.api_key
        }
    
    async def get_wallet_history(self, wallet: str, chain: str, limit: int = 5):
        """
        Busca o histórico de transações de uma carteira
        
        Args:
            wallet: Endereço da carteira
            chain: Cadeia blockchain (ex: base, eth, polygon)
            limit: Número máximo de transações a retornar (padrão: 5)
        
        Returns:
            dict: Resposta da API da Moralis
        """
        url = f"{self.base_url}/wallets/{wallet}/history"
        params = {
            "chain": chain.lower(),
            "limit": limit
        }
        
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url, params=params, headers=self.headers)
                
                if response.status_code != 200:
                    raise Exception(f"Erro na API Moralis - Status: {response.status_code}, Mensagem: {response.text}")
                
                return response.json()
                
        except httpx.RequestError as e:
            raise Exception(f"Erro de conexão com Moralis: {e}")
        except Exception as e:
            raise Exception(f"Erro ao buscar histórico: {str(e)}")
    
    async def get_wallet_tokens(self, wallet: str, chain: str):
        """
        Busca os tokens de uma carteira
        
        Args:
            wallet: Endereço da carteira
            chain: Cadeia blockchain (ex: base, eth, polygon)
        
        Returns:
            dict: Resposta da API da Moralis
        """
        url = f"{self.base_url}/wallets/{wallet}/tokens"
        params = {
            "chain": chain.lower()
        }
        
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url, params=params, headers=self.headers)
                
                if response.status_code != 200:
                    raise Exception(f"Erro na API Moralis - Status: {response.status_code}, Mensagem: {response.text}")
                
                return response.json()
                
        except httpx.RequestError as e:
            raise Exception(f"Erro de conexão com Moralis: {e}")
        except Exception as e:
            raise Exception(f"Erro ao buscar tokens: {str(e)}")

# Instância global do serviço
moralis_service = MoralisService()

