"""
Authentication functions for Sentinel and COSMO-SkyMed APIs.
"""

import os
import logging
import requests
from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)

def authenticate_cosmo(analyzer, api_url: str = 'https://api.registration.cosmo-skymed.it/auth/login') -> bool:
    """Authenticate with the COSMO-SkyMed data portal."""
    try:
        # Validate credentials
        if not analyzer.cosmo_username or analyzer.cosmo_username == 'your-cosmo-username':
            logger.error("Invalid COSMO-SkyMed username. Please update your .env file")
            return False
        if not analyzer.cosmo_password or analyzer.cosmo_password == 'your-cosmo-password':
            logger.error("Invalid COSMO-SkyMed password. Please update your .env file")
            return False
        
        logger.info(f"Attempting to authenticate with COSMO-SkyMed")
        
        try:
            response = requests.post(
                api_url,
                json={
                    "username": analyzer.cosmo_username,
                    "password": analyzer.cosmo_password
                },
                timeout=30
            )
            
            response.raise_for_status()  # Raise exception for bad status codes
            
            auth_data = response.json()
            if not auth_data.get('token'):
                logger.error("No authentication token received")
                return False
                
            analyzer.cosmo_api_token = auth_data['token']
            logger.info("Successfully authenticated with COSMO-SkyMed")
            return True
            
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to COSMO-SkyMed API. Please check your internet connection.")
            return False
        except requests.exceptions.Timeout:
            logger.error("Connection timed out. Please try again.")
            return False
        except requests.exceptions.HTTPError as e:
            logger.error(f"Authentication failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Setup error: {e}")
        return False

def authenticate(analyzer, api_url: str) -> bool:
    """Authenticate with the COSMO-SkyMed data portal."""
    data = {
        'client_id': analyzer.client_id,
        'client_secret': analyzer.client_secret,
        'grant_type': 'client_credentials',
    }

    logger.info("Attempting to authenticate with COPERNICUS")

    try:
        response = requests.post(api_url, data=data)

        # Check if the request was successful
        if response.status_code != 200:
            logger.error(f"Authentication failed: {response.status_code}")
            return False

        # Try parsing the response JSON
        try:
            response_data = response.json()
            analyzer.api = response_data.get('token', None) or os.getenv('ACCESS_TOKEN')

            if not analyzer.api:
                logger.error("Authentication failed: Token not found in response")
                return False

        except ValueError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return False

        logger.debug(response_data)
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return False



