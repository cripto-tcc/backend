# Projeto: Backend de Cotações de Criptomoedas com IA

Este projeto é um backend em Python usando FastAPI, que processa solicitações de usuários para operações de criptomoedas, especialmente cotações de troca de tokens. Ele utiliza a OpenAI para entender a intenção do usuário e extrair informações relevantes do texto, e integra com o serviço LI.FI para obter cotações de swaps de tokens.

## Como funciona

1. O usuário envia uma requisição com:
   - `walletAddress`: endereço da carteira
   - `chain`: blockchain desejada (ex: ETH)
   - `input`: texto livre descrevendo a operação desejada (ex: "Quero trocar 10 BTC por USDC")
2. O backend usa a OpenAI para:
   - Classificar a intenção do usuário (cotação, swap, transferência, etc.)
   - Extrair tokens e valores do texto, se necessário
3. Se a intenção for cotação:
   - O sistema consulta o LI.FI para obter a cotação de troca entre os tokens informados
   - O resultado é transformado em uma mensagem amigável para o usuário, usando novamente a OpenAI

## Estrutura do Projeto

- `main.py`: ponto de entrada da API FastAPI
- `agents/`: agentes responsáveis por orquestrar as operações (roteamento e cotação)
- `services/`: integrações com serviços externos (OpenAI e LI.FI)
- `models/`: modelos de dados (ex: UserRequest)

## Como rodar localmente

1. Instale as dependências:
   pip install -r requirements.txt

2. Configure as variáveis de ambiente:

   - Crie um arquivo `.env` na raiz do projeto, siga o exemplo da .env.example
     ```
     CORS_ORIGIN=url-porta-frontend (ex: http://localhost:5173)
     OPENAI_API_KEY=sua-chave-openai
     ```

3. Inicie o servidor FastAPI:
   uvicorn main:app --reload

## Exemplo de requisição

POST /process

```json
{
  "walletAddress": "0x1234567890abcdef1234567890abcdef12345678",
  "chain": "ETH",
  "input": "Se eu transformar 234000 USDC em WBTC, quantos wbtc eu teria?"
}
```

A resposta será uma mensagem amigável explicando a cotação obtida.
