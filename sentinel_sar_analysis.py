#!/usr/bin/env python3
"""
Sentinel SAR Data Analysis Tool

This script is a work in progress and is not yet complete. It is intended to be used as a tool for analyzing Sentinel SAR data.
Author: Alberto Barrago
"""

import datetime
import logging

from dotenv import load_dotenv
from sentinel_sar.analyzer import SARAnalyzer
import os

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the SAR analysis tool."""
    logger.info("\n=== SAR Data Analysis Tool ===")
    logger.info("This tool fetches and analyzes SAR data to detect potential subsurface features.")
    
    analyzer = SARAnalyzer(
        client_id=os.getenv('CLIENT_ID'),
        client_secret=os.getenv('CLIENT_SECRET')
    )
    
    # Default coordinates (Giza, Egypt)
    giza_coords = {
        'min_lon': 31.0,
        'min_lat': 29.9,
        'max_lon': 31.2,
        'max_lat': 30.1
    }
    
    try:
        # Get coordinates with validation
        coords = {}
        for key, default in giza_coords.items():
            while True:
                try:
                    value = input(f"{key} [{default}]: ").strip() or default
                    coords[key] = float(value)
                    break
                except ValueError:
                    logger.error("Please enter a valid number")
        
        # Get date range
        today = datetime.datetime.now()
        one_year_ago = today - datetime.timedelta(days=365)
        
        start_date = input(f"Start date [{one_year_ago.strftime('%Y%m%d')}]: ") or one_year_ago.strftime('%Y%m%d')
        end_date = input(f"End date [{today.strftime('%Y%m%d')}]: ") or today.strftime('%Y%m%d')
        
        # Ask for orbit direction
        orbit_direction = input("Orbit direction (ASCENDING/DESCENDING) [ASCENDING]: ").upper() or "ASCENDING"
        
        # Ask for sensor mode
        sensor_mode = input("Sensor mode (IW/EW/SM/WV) [IW]: ").upper() or "IW"
        
        logger.info("\nStarting analysis...")
        # In the main function, make sure the analyze_area call matches the method definition
        if analyzer.analyze_area(
            coords['min_lon'],
            coords['min_lat'],
            coords['max_lon'], 
            coords['max_lat'],
            start_date,
            end_date,
            orbit_direction=orbit_direction,
            sensor_mode=sensor_mode
        ):
            logger.info("\nAnalysis completed successfully!")
            logger.info(f"Results saved to {analyzer.download_path / 'sar_analysis_results.png'}")
        else:
            logger.error("\nAnalysis failed. Please check the error messages above.")
            
    except KeyboardInterrupt:
        logger.info("\nAnalysis cancelled by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
