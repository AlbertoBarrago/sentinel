"""
Authentication functions for Sentinel and COSMO-SkyMed APIs.
"""

import logging
from getpass import getpass
import requests
from sentinelsat import SentinelAPI

logger = logging.getLogger(__name__)

def authenticate(analyzer, api_url: str = 'https://apihub.copernicus.eu/apihub') -> bool:
    """Authenticate with the Copernicus Data Space Ecosystem or Open Access Hub."""
    try:
        # Check if we're using the new CDSE API
        if 'dataspace.copernicus.eu' in api_url or 'catalogue.dataspace.copernicus.eu' in api_url:
            if not analyzer.client_id:
                analyzer.client_id = input("Enter your Copernicus Data Space client ID: ")
            if not analyzer.client_secret:
                analyzer.client_secret = getpass("Enter your Copernicus Data Space client secret: ")
            
            logger.info(f"Attempting to authenticate with CDSE at {api_url}")
            # For CDSE, we use the client_id as username and client_secret as password
            analyzer.api = SentinelAPI(
                analyzer.client_id,
                analyzer.client_secret,
                api_url
            )
        else:
            # Traditional username/password for older APIs
            if not analyzer.username:
                analyzer.username = input("Enter your Copernicus username: ")
            if not analyzer.password:
                analyzer.password = getpass("Enter your Copernicus password: ")
            
            logger.info(f"Attempting to authenticate with {api_url}")
            analyzer.api = SentinelAPI(
                analyzer.username, 
                analyzer.password, 
                api_url
            )
        return True
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        logger.info("Note: For the new Copernicus Data Space Ecosystem, you need to register at https://dataspace.copernicus.eu/ and create API credentials")
        return False

def authenticate_cosmo(analyzer, api_url: str = 'https://api.registration.cosmo-skymed.it/auth/login') -> bool:
    """Authenticate with the COSMO-SkyMed data portal."""
    try:
        if not analyzer.cosmo_username:
            analyzer.cosmo_username = input("Enter your COSMO-SkyMed username: ")
        if not analyzer.cosmo_password:
            analyzer.cosmo_password = getpass("Enter your COSMO-SkyMed password: ")
        
        logger.info(f"Attempting to authenticate with COSMO-SkyMed at {api_url}")
        
        # Create the authentication payload
        payload = {
            "username": analyzer.cosmo_username,
            "password": analyzer.cosmo_password
        }
        
        # Make the authentication request
        response = requests.post(api_url, json=payload)
        
        if response.status_code == 200:
            auth_data = response.json()
            analyzer.cosmo_api_token = auth_data.get('token')
            if analyzer.cosmo_api_token:
                logger.info("Successfully authenticated with COSMO-SkyMed")
                return True
            else:
                logger.error("Authentication response did not contain a token")
                return False
        else:
            logger.error(f"Authentication failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"COSMO-SkyMed authentication failed: {e}")
        logger.info("Note: You need to register at https://registration.cosmo-skymed.it/ to access COSMO-SkyMed data")
        return False