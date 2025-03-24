#!/usr/bin/env python3
"""
Sentinel SAR Data Analysis Tool

Disclaimer: Work in progress...

This script fetches and analyzes Synthetic Aperture Radar (SAR) data from Copernicus
using the sentinelsat library. It allows for data acquisition based on coordinates,
processing the imagery using rasterio, and applying signal processing techniques
to detect subsurface anomalies.

Requirements:
    - sentinelsat
    - rasterio 
    - numpy
    - matplotlib
    - scipy
"""

from typing import Optional, Dict, List, Tuple, Any
import os
import sys
import datetime
import logging
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
from datetime import date
import rasterio
from rasterio.errors import RasterioIOError
from rasterio.plot import show
from scipy import signal, ndimage
from shapely.geometry import box
import geopandas as gpd
from getpass import getpass
import requests
from sentinel_sar.analyzer import SARAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the SAR analysis tool."""
    logger.info("\n=== SAR Data Analysis Tool ===")
    logger.info("This tool fetches and analyzes SAR data to detect potential subsurface features.")
    
    analyzer = SARAnalyzer()
    
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
        
        # Ask for data source
        data_source = input("Data source (sentinel/cosmo) [sentinel]: ").lower() or "sentinel"
        
        logger.info("\nStarting analysis...")
        if analyzer.analyze_area(
            coords['min_lon'],
            coords['min_lat'],
            coords['max_lon'], 
            coords['max_lat'],
            start_date,
            end_date,
            data_source
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
