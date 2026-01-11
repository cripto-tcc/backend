# Cryptocurrency Trading Chatbot Backend

<img width="1200" height="1200" alt="image" src="https://github.com/user-attachments/assets/8b0a0a29-d55e-4a9b-a75d-de4c394f5310" />


## Project Summary

This is a **cryptocurrency trading chatbot backend** that enables users to perform cryptocurrency operations through natural language interactions. The system supports various operations including:

- **Swaps**: Exchange one cryptocurrency for another
- **Transfers**: Send cryptocurrencies between wallets
- **Quotes**: Get real-time exchange rates and conversion estimates

Users can interact with the system using plain language (e.g., "I want to swap 10 BTC for USDC" or "How many WBTC would I get for 234,000 USDC?"), and the AI-powered backend processes these requests to execute the desired operations.

---

## Project: Cryptocurrency Quotes Backend with AI

This project is a Python backend using FastAPI that processes user requests for cryptocurrency operations, especially token swap quotes. It uses Gemini 2.0 Flash to understand user intent and extract relevant information from text, and integrates with the LI.FI service to obtain token swap quotes.

## How it works

1. The user sends a request with:
   - `walletAddress`: wallet address
   - `chain`: desired blockchain (e.g., ETH)
   - `input`: free text describing the desired operation (e.g., "I want to swap 10 BTC for USDC")
2. The backend uses Gemini 2.0 Flash to:
   - Classify the user's intent (quote, swap, transfer, etc.)
   - Extract tokens and values from the text, if necessary
3. If the intent is a quote:
   - The system queries LI.FI to obtain the swap quote between the specified tokens
   - The result is transformed into a user-friendly message using Gemini 2.0 Flash again

## Project Structure

- `main.py`: FastAPI entry point
- `agents/`: agents responsible for orchestrating operations (routing and quotes)
- `services/`: integrations with external services (Gemini 2.0 Flash and LI.FI)
- `models/`: data models (e.g., UserRequest)

## How to run locally

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:

   - Create a `.env` file in the project root, following the example from `.env.example`:
     ```
     CORS_ORIGIN=frontend-url-port (e.g., http://localhost:5173)
     GEMINI_API_KEY=gemini-api-key
     ```

3. Start the FastAPI server:
```bash
uvicorn main:app --reload
```
   or
```bash
python -m uvicorn main:app --reload
```
   (for Git Bash on Windows terminals)

## Example request

POST /process

```json
{
  "walletAddress": "0x1234567890abcdef1234567890abcdef12345678",
  "chain": "ETH",
  "input": "If I convert 234000 USDC to WBTC, how many wbtc would I have?"
}
```

The response will be a user-friendly message explaining the obtained quote.
