"""
Command-line interface for the Sentinel SAR Analysis package.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dotenv import load_dotenv

from sentinel_sar.analyzer import SARAnalyzer
from sentinel_sar.utils import setup_logging, validate_coordinates, validate_date_range

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Sentinel SAR Analysis Tool - Fetch and analyze SAR data from Copernicus and COSMO-SkyMed satellites"
    )
    
    # Authentication options
    auth_group = parser.add_argument_group("Authentication Options")
    auth_group.add_argument("--username", help="Copernicus Open Access Hub username")
    auth_group.add_argument("--password", help="Copernicus Open Access Hub password")
    auth_group.add_argument("--client-id", help="Copernicus Data Space Ecosystem client ID")
    auth_group.add_argument("--client-secret", help="Copernicus Data Space Ecosystem client secret")
    auth_group.add_argument("--cosmo-username", help="COSMO-SkyMed username")
    auth_group.add_argument("--cosmo-password", help="COSMO-SkyMed password")
    auth_group.add_argument("--env-file", help="Path to .env file with credentials", default=".env")
    
    # Area of interest options
    aoi_group = parser.add_argument_group("Area of Interest Options")
    aoi_group.add_argument("--min-lon", type=float, help="Minimum longitude")
    aoi_group.add_argument("--min-lat", type=float, help="Minimum latitude")
    aoi_group.add_argument("--max-lon", type=float, help="Maximum longitude")
    aoi_group.add_argument("--max-lat", type=float, help="Maximum latitude")
    aoi_group.add_argument("--preset", choices=["giza", "pyramids"], 
                          help="Use a preset area of interest")
    
    # Date range options
    date_group = parser.add_argument_group("Date Range Options")
    date_group.add_argument("--start-date", help="Start date (format: YYYYMMDD)")
    date_group.add_argument("--end-date", help="End date (format: YYYYMMDD)")
    
    # Data source options
    source_group = parser.add_argument_group("Data Source Options")
    source_group.add_argument("--source", choices=["sentinel", "cosmo"], default="sentinel",
                             help="Data source (default: sentinel)")
    
    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument("--output-dir", help="Output directory for downloaded and processed data")
    output_group.add_argument("--limit", type=int, default=1, 
                             help="Maximum number of products to download (default: 1)")
    output_group.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    # Action options
    action_group = parser.add_argument_group("Action Options")
    action_group.add_argument("--search-only", action="store_true", 
                             help="Only search for products, don't download or process")
    action_group.add_argument("--download-only", action="store_true",
                             help="Download products but don't process them")
    
    return parser.parse_args()

def get_preset_coordinates(preset: str) -> Tuple[float, float, float, float]:
    """Get preset coordinates for common areas of interest."""
    presets = {
        "giza": (31.0, 29.9, 31.2, 30.1),  # Giza Plateau, Egypt
        "pyramids": (31.12, 29.96, 31.14, 29.98),  # Great Pyramids of Giza (more focused)
    }
    
    return presets.get(preset, (0, 0, 0, 0))

def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logging(level=log_level)
    
    # Load environment variables if .env file exists
    if os.path.exists(args.env_file):
        load_dotenv(args.env_file)
    
    # Get credentials from arguments or environment variables
    username = args.username or os.getenv("COPERNICUS_USERNAME")
    password = args.password or os.getenv("COPERNICUS_PASSWORD")
    client_id = args.client_id or os.getenv("CLIENT_ID")
    client_secret = args.client_secret or os.getenv("CLIENT_SECRET")
    cosmo_username = args.cosmo_username or os.getenv("COSMO_USERNAME")
    cosmo_password = args.cosmo_password or os.getenv("COSMO_PASSWORD")
    
    # Create the SARAnalyzer instance
    analyzer = SARAnalyzer(
        username=username,
        password=password,
        client_id=client_id,
        client_secret=client_secret,
        cosmo_username=cosmo_username,
        cosmo_password=cosmo_password
    )
    
    # Set output directory if specified
    if args.output_dir:
        analyzer.download_path = Path(args.output_dir)
        analyzer.download_path.mkdir(exist_ok=True)
    
    # Get coordinates
    if args.preset:
        min_lon, min_lat, max_lon, max_lat = get_preset_coordinates(args.preset)
        logger.info(f"Using preset coordinates for {args.preset}")
    else:
        min_lon = args.min_lon
        min_lat = args.min_lat
        max_lon = args.max_lon
        max_lat = args.max_lat
    
    # Validate coordinates
    if not all([min_lon is not None, min_lat is not None, max_lon is not None, max_lat is not None]):
        logger.error("Coordinates are required. Use --min-lon, --min-lat, --max-lon, --max-lat or --preset")
        sys.exit(1)
    
    if not validate_coordinates(min_lon, min_lat, max_lon, max_lat):
        sys.exit(1)
    
    # Get date range
    start_date = args.start_date or "20230101"  # Default to January 1, 2023
    end_date = args.end_date or "20231231"      # Default to December 31, 2023
    
    # Validate date range
    if not validate_date_range(start_date, end_date):
        sys.exit(1)
    
    # Create the footprint
    footprint = analyzer.create_aoi_from_coordinates(min_lon, min_lat, max_lon, max_lat)
    
    # Authenticate with the appropriate API
    if args.source.lower() == "cosmo":
        if not analyzer.authenticate_cosmo():
            logger.error("Failed to authenticate with COSMO-SkyMed API")
            sys.exit(1)
    else:
        if not analyzer.authenticate():
            logger.error("Failed to authenticate with Copernicus API")
            sys.exit(1)
    
    # Search for products
    if args.source.lower() == "cosmo":
        products = analyzer.search_cosmo_data(footprint, start_date, end_date)
    else:
        products = analyzer.search_sar_data(footprint, start_date, end_date)
    
    if not products:
        logger.warning("No products found for the specified parameters")
        sys.exit(0)
    
    # If search-only flag is set, exit after search
    if args.search_only:
        logger.info("Search completed. Exiting as requested.")
        sys.exit(0)
    
    # Download products
    if args.source.lower() == "cosmo":
        downloaded_files = analyzer.download_cosmo_products(limit=args.limit)
    else:
        downloaded_files = analyzer.download_products(limit=args.limit)
    
    if not downloaded_files:
        logger.error("Failed to download any products")
        sys.exit(1)
    
    # If download-only flag is set, exit after download
    if args.download_only:
        logger.info("Download completed. Exiting as requested.")
        sys.exit(0)
    
    # Process the downloaded files
    for file_path in downloaded_files:
        logger.info(f"Processing {file_path}...")
        
        if args.source.lower() == "cosmo":
            processed_file = analyzer.process_cosmo_data(file_path)
        else:
            processed_file = analyzer.process_sentinel1_data(file_path)
        
        if processed_file:
            # Preprocess the data
            processed_data = analyzer.preprocess_sar_data(processed_file)
            
            if processed_data is not None:
                # Detect subsurface features
                features = analyzer.detect_subsurface_features(processed_data)
                
                if features is not None:
                    try:
                        import rasterio
                        with rasterio.open(processed_file) as src:
                            original_data = src.read(1)
                            geotransform = src.transform
                            crs = src.crs
                        
                        # Visualize the results
                        analyzer.visualize_results(
                            original_data, 
                            processed_data, 
                            features,
                            title=f"{args.source.capitalize()} SAR Analysis Results"
                        )
                        
                        # Create an interactive map if possible
                        try:
                            from sentinel_sar.visualization import create_interactive_map
                            create_interactive_map(
                                analyzer,
                                original_data,
                                geotransform,
                                crs,
                                title=f"{args.source.capitalize()} SAR Data Map"
                            )
                        except ImportError:
                            logger.warning("Could not create interactive map. Install folium for this feature.")
                        
                    except Exception as e:
                        logger.error(f"Error visualizing results: {e}")
    
    logger.info("Analysis completed successfully!")

if __name__ == "__main__":
    main()