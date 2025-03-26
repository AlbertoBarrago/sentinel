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
    
    # Predefined locations with good SAR coverage
    locations = {
        "giza": {
            'name': "Giza, Egypt",
            'min_lon': 31.0,
            'min_lat': 29.9,
            'max_lon': 31.2,
            'max_lat': 30.1
        },
        "venice": {
            'name': "Venice, Italy",
            'min_lon': 12.2,
            'min_lat': 45.4,
            'max_lon': 12.4,
            'max_lat': 45.5
        },
        "amazon": {
            'name': "Amazon Rainforest",
            'min_lon': -60.0,
            'min_lat': -3.0,
            'max_lon': -59.8,
            'max_lat': -2.8
        },
        "alps": {
            'name': "Swiss Alps",
            'min_lon': 8.0,
            'min_lat': 46.5,
            'max_lon': 8.2,
            'max_lat': 46.7
        },
        "netherlands": {
            'name': "Netherlands (Rotterdam)",
            'min_lon': 4.4,
            'min_lat': 51.9,
            'max_lon': 4.5,
            'max_lat': 52.0
        },
        "san_francisco": {
            'name': "San Francisco Bay Area",
            'min_lon': -122.5,
            'min_lat': 37.7,
            'max_lon': -122.3,
            'max_lat': 37.9
        }
    }
    
    # Display available locations
    logger.info("\nAvailable locations:")
    for key, loc in locations.items():
        logger.info(f"  {key}: {loc['name']}")
    
    # Get location choice
    while True:
        location_choice = input("\nSelect location (giza/venice/amazon/alps) [giza]: ").lower() or "giza"
        if location_choice in locations:
            selected_location = locations[location_choice]
            logger.info(f"Selected location: {selected_location['name']}")
            break
        else:
            logger.error("Invalid location. Please select from the available options.")
    
    try:
        # Get coordinates with validation
        coords = {}
        for key in ['min_lon', 'min_lat', 'max_lon', 'max_lat']:
            default = selected_location[key]
            while True:
                try:
                    value = input(f"{key} [{default}]: ").strip() or default
                    coords[key] = float(value)
                    break
                except ValueError:
                    logger.error("Please enter a valid number")
        
        # Get date range
        today = datetime.datetime.now()
        three_years_ago = today - datetime.timedelta(days=1095)  # 3 years for better data availability
        
        start_date = input(f"Start date [{three_years_ago.strftime('%Y%m%d')}]: ") or three_years_ago.strftime('%Y%m%d')
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
