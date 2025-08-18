"""
Serviço para normalizar nomes de tokens digitados pelo usuário.
Mapeia nomes comuns, abreviações e variações para as siglas oficiais dos tokens.
"""

class TokenNormalizer:
    
    # Mapeamento de variações de nomes para siglas oficiais de tokens
    # Apenas tokens disponíveis nas redes: Ethereum (ETH), Polygon (POL) e Base (BAS)
    TOKEN_MAPPINGS = {
        # Ethereum (nativo em ETH e BASE)
        "ethereum": "ETH",
        "ether": "ETH",
        "eth": "ETH",
        "weth": "WETH",
        "wrapped ethereum": "WETH",
        "wrapped eth": "WETH",
        
        # Bitcoin (disponível como WBTC em ETH, Polygon e Base)
        "bitcoin": "WBTC",
        "btc": "WBTC",
        "wbtc": "WBTC",
        "wrapped bitcoin": "WBTC",
        "wrapped btc": "WBTC",
        
        # USDC (disponível em ETH, Polygon e Base)
        "usdc": "USDC",
        "usd coin": "USDC",
        "dollar coin": "USDC",
        "usdc coin": "USDC",
        "circle coin": "USDC",
        "dollar": "USDC",
        "dolar": "USDC",
        "usd": "USDC",
        
        # USDT (disponível em ETH e Polygon)
        "usdt": "USDT",
        "tether": "USDT",
        "tether usd": "USDT",
        "dollar tether": "USDT",
        
        # Polygon tokens (rede Polygon)
        "matic": "MATIC",           # Token antigo, ainda usado
        "pol": "POL",               # Token nativo atual da Polygon
        "polygon": "POL",           # Nome da rede -> token nativo atual
        "polygon ecosystem token": "POL",
        "wmatic": "WMATIC",         # MATIC wrapped
        "wrapped matic": "WMATIC",
        
        # DAI (disponível em ETH, Polygon e Base)
        "dai": "DAI",
        "dai stablecoin": "DAI",
        
        # Chainlink (disponível em ETH, Polygon e Base)
        "link": "LINK",
        "chainlink": "LINK",
        
        # Uniswap (disponível em ETH, Polygon e Base)
        "uni": "UNI",
        "uniswap": "UNI",
        
        # Aave (disponível em ETH e Polygon)
        "aave": "AAVE",
        
        # Compound (disponível em ETH)
        "comp": "COMP",
        "compound": "COMP",
        
        # Maker (disponível em ETH)
        "mkr": "MKR",
        "maker": "MKR",
        
        # Arbitrum (disponível em ETH)
        "arb": "ARB",
        "arbitrum": "ARB",
        
        # Optimism (disponível em ETH)
        "op": "OP",
        "optimism": "OP",
        
        # Stablecoins adicionais disponíveis nessas redes
        "frax": "FRAX",  # ETH, Polygon
        "tusd": "TUSD",  # ETH, Polygon
        "true usd": "TUSD",
        "lusd": "LUSD",  # ETH
        
        # Tokens específicos do ecossistema Polygon
        "quickswap": "QUICK",
        "quick": "QUICK",
        
        # Shiba Inu (disponível em ETH, Polygon)
        "shib": "SHIB",
        "shiba inu": "SHIB",
        
        # Pepe (disponível em ETH)
        "pepe": "PEPE",
        
        # 1inch (disponível em ETH, Polygon)
        "1inch": "1INCH",
        "one inch": "1INCH",
        
        # Curve (disponível em ETH, Polygon)
        "crv": "CRV",
        "curve": "CRV",
        
        # Synthetix (disponível em ETH)
        "snx": "SNX",
        "synthetix": "SNX",
        
        # Balancer (disponível em ETH, Polygon)
        "bal": "BAL",
        "balancer": "BAL",
        
        # SushiSwap (disponível em ETH, Polygon)
        "sushi": "SUSHI",
        "sushiswap": "SUSHI",
        
        # Yearn Finance (disponível em ETH)
        "yfi": "YFI",
        "yearn": "YFI",
        "yearn finance": "YFI",
    }
    
    @classmethod
    def normalize_token(cls, token_input):
        """
        Normaliza a entrada do usuário para a sigla oficial do token.
        
        Args:
            token_input (str): Nome do token digitado pelo usuário
            
        Returns:
            str: Sigla oficial do token ou a entrada original se não encontrada
        """
        if not token_input:
            return token_input
            
        # Remove espaços extras e converte para minúsculo
        normalized_input = token_input.strip().lower()
        
        # Verifica se existe um mapeamento direto
        if normalized_input in cls.TOKEN_MAPPINGS:
            return cls.TOKEN_MAPPINGS[normalized_input]
        
        # Se não encontrou mapeamento, retorna a entrada original em maiúsculo
        # (caso já seja uma sigla correta)
        return token_input.upper()
    
    @classmethod
    def normalize_extracted_data(cls, extracted_data):
        """
        Normaliza os tokens extraídos dos dados do usuário.
        
        Args:
            extracted_data (dict): Dados extraídos contendo fromToken e toToken
            
        Returns:
            dict: Dados com tokens normalizados
        """
        normalized_data = extracted_data.copy()
        
        if "fromToken" in normalized_data:
            normalized_data["fromToken"] = cls.normalize_token(normalized_data["fromToken"])
        
        if "toToken" in normalized_data:
            normalized_data["toToken"] = cls.normalize_token(normalized_data["toToken"])
            
        if "token" in normalized_data:  # Para transferências
            normalized_data["token"] = cls.normalize_token(normalized_data["token"])
        
        return normalized_data
