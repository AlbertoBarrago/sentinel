#!/usr/bin/env python3
"""
Example usage of the Sentinel SAR Analysis Tool

This script demonstrates how to use the SARAnalyzer class to analyze
SAR data for a specific area of interest.
"""

from sentinel_sar_analysis import SARAnalyzer
import logging
import os
from dotenv import load_dotenv


load_dotenv()


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Create an instance of the SARAnalyzer with CDSE credentials
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    
    # Try using the traditional API endpoint first
    analyzer = SARAnalyzer(username=client_id, password=client_secret)
    
    # Try to authenticate with the traditional API endpoint
    if not analyzer.authenticate(api_url=os.getenv('API_URL') or 'https://apihub.copernicus.eu/apihub'):
        logger.error("Authentication failed with traditional endpoint. Trying CDSE endpoint...")
        
        # Try with the CDSE endpoint
        analyzer = SARAnalyzer(client_id=client_id, client_secret=client_secret)
        if not analyzer.authenticate(api_url='https://catalogue.dataspace.copernicus.eu/api/hub'):
            logger.error("Authentication failed with CDSE endpoint. Please check your credentials.")
            return
    
    # Define the area of interest (Giza, Egypt)
    min_lon = 31.0
    min_lat = 29.9
    max_lon = 31.2
    max_lat = 30.1
    
    # Define the date range (use a more recent timeframe)
    start_date = "20230601"  # June 1, 2023
    end_date = "20231231"    # December 31, 2023
    
    # Create the footprint
    footprint = analyzer.create_aoi_from_coordinates(min_lon, min_lat, max_lon, max_lat)
    
    # Search for products directly
    logger.info("Searching for SAR data...")
    products = analyzer.search_sar_data(footprint, start_date, end_date)
    
    if not products:
        logger.warning("No products found. Try adjusting your search parameters.")
        return
    
    # If products were found, continue with download and analysis
    logger.info(f"Found {len(products)} products. Downloading...")
    downloaded_files = analyzer.download_products(limit=1)
    
    if not downloaded_files:
        logger.error("Failed to download any products.")
        return
    
    # Process the downloaded files
    for file_path in downloaded_files:
        logger.info(f"Processing {file_path}...")
        # Continue with your analysis...

if __name__ == "__main__":
    main()