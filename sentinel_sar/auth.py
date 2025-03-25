
import os
import logging
import requests
from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)

def authenticate(analyzer, api_url: str = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token') -> bool:
    """Authenticate with the Copernicus Data Space Ecosystem."""
    try:
        # Check if client credentials are provided
        if not analyzer.client_id or not analyzer.client_secret:
            logger.error("Client ID and Client Secret are required for authentication")
            return False
            
        # Log authentication attempt
        logger.info(f"Authenticating with Copernicus Data Space Ecosystem")
        
        # Set up the authentication payload
        payload = {
            'grant_type': 'client_credentials',
            'client_id': analyzer.client_id,
            'client_secret': analyzer.client_secret
        }
        
        # Make the authentication request
        response = requests.post(api_url, data=payload)
        
        if response.status_code == 200:
            token_data = response.json()
            analyzer.api = token_data.get('access_token')
            logger.info("Authentication successful")
            return True
        else:
            logger.error(f"Authentication failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return False



