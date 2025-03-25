"""
Authentication functions for Sentinel and COSMO-SkyMed APIs.
"""

import logging
import requests
from sentinelsat import SentinelAPI
import os
from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)

def authenticate_copernicus(analyzer, api_url: str = os.getenv('COPERNICUS_API_URL') or 'https://apihub.copernicus.eu/apihub') -> bool:
    """Authenticate with the Copernicus Data Space Ecosystem or Open Access Hub."""
    try:
        if 'copernicus.eu/apihub' in api_url:
            if not analyzer.client_id or analyzer.client_id == 'your-client-id':
                logger.error("Invalid client ID. Please update your .env file with valid credentials")
                return False
            if not analyzer.client_secret or analyzer.client_secret == 'your-client-secret':
                logger.error("Invalid client secret. Please update your .env file with valid credentials")
                return False
                
            credentials = (analyzer.client_id, analyzer.client_secret)
            logger.info("Using CDSE authentication")
            
        else: 
            if not analyzer.username or analyzer.username == 'your-username':
                logger.error("Invalid username. Please update your .env file with valid credentials")
                return False
            if not analyzer.password or analyzer.password == 'your-password':
                logger.error("Invalid password. Please update your .env file with valid credentials")
                return False
                
            credentials = (analyzer.username, analyzer.password)
            logger.info("Using traditional API authentication")

        # Test connection and credentials
        try:
            logger.info(f"Attempting to authenticate with {api_url}")
            analyzer.api = SentinelAPI(*credentials, api_url)
            
            logger.info("Authentication successful!")
            return True
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to {api_url}. Please check your internet connection.")
            return False
        except requests.exceptions.HTTPError as e:
            if '401' in str(e):
                logger.error("Authentication failed: Invalid credentials")
            elif '403' in str(e):
                logger.error("Authentication failed: Access forbidden")
            else:
                logger.error(f"HTTP Error: {e}")
            return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Setup error: {e}")
        return False

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