"""
Processing functions for SAR data.
"""

import os
import datetime
import logging
import numpy as np
from sentinelsat import read_geojson, geojson_to_wkt
import rasterio
from rasterio.errors import RasterioIOError
from scipy import ndimage
from shapely.geometry import box
import geopandas as gpd
import requests
import traceback
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

def create_aoi_from_coordinates(analyzer, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
    """Create an Area of Interest (AOI) from coordinates."""
    try:
        # Create a bounding box
        bbox = box(min_lon, min_lat, max_lon, max_lat)
        
        # Convert to GeoDataFrame
        geo_df = gpd.GeoDataFrame({'geometry': [bbox]}, crs='EPSG:4326')
        
        # Save to a temporary GeoJSON file
        temp_geojson = analyzer.download_path / 'temp_aoi.geojson'
        geo_df.to_file(temp_geojson, driver='GeoJSON')
        
        # Convert to WKT
        footprint = geojson_to_wkt(read_geojson(str(temp_geojson)))
        return footprint
    except Exception as e:
        logger.error(f"Error creating AOI: {e}")
        return ""

def search_sar_data(analyzer, footprint: str, start_date: str, end_date: str, 
                   platform_name: str = 'Sentinel-1', orbit_direction: str = 'ASCENDING',
                   sensor_mode: str = 'IW') -> Dict:
    """Search for SAR data within the specified parameters."""
    try:
        # Check if API token is available
        if not analyzer.api:
            logger.error("API token not available. Call authenticate() first.")
            return {}
            
        # Convert string dates to datetime objects
        try:
            start = datetime.datetime.strptime(start_date, '%Y%m%d').date()
            # Extend search period to 5 years back to increase chances of finding data
            extended_start = start - datetime.timedelta(days=1825)  # 5 years
        except ValueError:
            logger.warning(f"Invalid start date format: {start_date}, using 5 years ago")
            start = datetime.datetime.now().date()
            extended_start = start - datetime.timedelta(days=1825)
            
        try:
            end = datetime.datetime.strptime(end_date, '%Y%m%d').date()
        except ValueError:
            logger.warning(f"Invalid end date format: {end_date}, using today")
            end = datetime.datetime.now().date()
        
        # Use the correct OpenSearch API endpoint
        search_url = "https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel1/search.json"
        
        # Set up headers with the token
        headers = {
            'Authorization': f'Bearer {analyzer.api}',
            'Accept': 'application/json'
        }
        
        # Try a direct API request with minimal parameters
        logger.info("Trying direct API request with minimal parameters")
        
        # Simplify the geometry to a point in the center of the bounding box
        import re
        coords = re.findall(r'[\d.]+', footprint)
        if len(coords) >= 8:  # At least 4 coordinate pairs
            # Calculate center point
            min_lon = float(coords[0])
            min_lat = float(coords[1])
            max_lon = float(coords[2])
            max_lat = float(coords[3])
            center_lon = (min_lon + max_lon) / 2
            center_lat = (min_lat + max_lat) / 2
            point_geometry = f"POINT({center_lon} {center_lat})"
            
            # Create a simple query with just the center point and date range
            simple_params = {
                'geometry': point_geometry,
                'startDate': f'{extended_start.isoformat()}',
                'completionDate': f'{end.isoformat()}',
                'maxRecords': 50  # Request more records
            }
            
            logger.info(f"Using simplified point geometry: {point_geometry}")
            logger.info(f"Search parameters: {simple_params}")
            
            response = requests.get(search_url, params=simple_params, headers=headers)
            
            if response.status_code == 200:
                products_data = response.json()
                features = products_data.get('features', [])
                logger.info(f"Found {len(features)} products with simplified point geometry")
                
                if features:
                    analyzer.products = features
                    return analyzer.products
            else:
                logger.error(f"API request failed with status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                
                # Check if token is valid
                logger.info("Checking if token is valid...")
                token_check_url = "https://catalogue.dataspace.copernicus.eu/resto/api/collections"
                token_response = requests.get(token_check_url, headers=headers)
                
                if token_response.status_code != 200:
                    logger.error("Token validation failed. Please re-authenticate.")
                    return {}
                else:
                    logger.info("Token is valid. The issue is with the search parameters.")
            
            # If we get here, try a completely different approach - use the collections endpoint
            logger.info("Trying collections endpoint to get any available Sentinel-1 data")
            collections_url = "https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel1/search.json"
            
            # Very minimal parameters - just get any recent Sentinel-1 data
            minimal_params = {
                'maxRecords': 10,
                'startDate': f'{extended_start.isoformat()}',
                'completionDate': f'{end.isoformat()}'
            }
            
            response = requests.get(collections_url, params=minimal_params, headers=headers)
            
            if response.status_code == 200:
                products_data = response.json()
                features = products_data.get('features', [])
                logger.info(f"Found {len(features)} products with minimal parameters")
                
                if features:
                    analyzer.products = features
                    return analyzer.products
            
        # If we get here, no products were found with any strategy
        logger.error("No products found with any search strategy")
        logger.info("Please try the following:")
        logger.info("1. Check that your API token is valid")
        logger.info("2. Try a different location with known Sentinel-1 coverage")
        logger.info("3. Try a wider date range")
        logger.info("4. Check the Copernicus Data Space Ecosystem website for service status")
        return {}
            
    except Exception as e:
        logger.error(f"Error searching for data: {e}")
        logger.debug(f"Detailed error: {traceback.format_exc()}")
        return {}



def download_products(analyzer, limit: int = 1) -> List[str]:
    """Download the found products."""
    if not analyzer.products or len(analyzer.products) == 0:
        logger.warning("No products to download. Run search_sar_data first.")
        return []
    
    try:
        # Check if API is authenticated
        if analyzer.api is None:
            logger.error("API not authenticated. Call authenticate() first.")
            return []
            
        # The products are now in a different format from the RESTO API
        # Sort products by ingestion date if available
        sorted_products = sorted(
            analyzer.products,
            key=lambda x: x.get('properties', {}).get('published', ''),
            reverse=True
        )
        
        # Select the most recent products up to the limit
        products_to_download = sorted_products[:limit]
        
        file_paths = []
        for product in products_to_download:
            try:
                # Get product ID and download URL
                product_id = product.get('id')
                product_title = product.get('properties', {}).get('title')
                
                if not product_id:
                    logger.warning(f"Could not find ID for product: {product_title}")
                    continue
                
                # Construct download URL
                download_url = f"https://catalogue.dataspace.copernicus.eu/resto/collections/Sentinel1/{product_id}/download"
                
                # Set up headers with the token
                headers = {
                    'Authorization': f'Bearer {analyzer.api}',
                    'Accept': 'application/json'
                }
                
                logger.info(f"Downloading product: {product_title}")
                
                # Make the download request
                response = requests.get(download_url, headers=headers, stream=True)
                
                if response.status_code == 200:
                    # Create a file path
                    file_path = analyzer.download_path / f"{product_title}.zip"
                    
                    # Download the file
                    with open(file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    logger.info(f"Successfully downloaded: {file_path}")
                    file_paths.append(str(file_path))
                else:
                    logger.error(f"Download failed with status code: {response.status_code}")
                    logger.error(f"Response: {response.text}")
            
            except Exception as e:
                logger.error(f"Error downloading product {product.get('properties', {}).get('title')}: {e}")
        
        return file_paths
    except Exception as e:
        logger.error(f"Error downloading products: {e}")
        logger.debug(f"Detailed error: {traceback.format_exc()}")
        return []



def process_sentinel1_data(analyzer, file_path: str) -> Optional[str]:
    """Process Sentinel-1 specific data format."""
    try:
        logger.info(f"Processing Sentinel-1 data: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error processing Sentinel-1 data: {e}")
        return None


def _lee_filter(img: np.ndarray, size: int) -> np.ndarray:
    """Apply Lee filter for speckle reduction."""
    img_mean = ndimage.uniform_filter(img, size=size)
    img_sqr_mean = ndimage.uniform_filter(img**2, size=size)
    img_variance = img_sqr_mean - img_mean**2
    
    # Compute the local variance
    overall_variance = np.var(img)
    
    # Lee filter
    img_weights = img_variance / (img_variance + overall_variance)
    img_output = img_mean + img_weights * (img - img_mean)
    
    return img_output

def preprocess_sar_data(analyzer, file_path: str) -> Optional[np.ndarray]:
    """Preprocess the SAR data for analysis."""
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            logger.error(f"Error: File does not exist at {file_path}")
            return None
        
        # Print file information for debugging
        logger.info(f"Attempting to process file: {file_path}")
        logger.info(f"File size: {os.path.getsize(file_path) / (1024*1024):.2f} MB")
        
        # Open the raster file
        with rasterio.open(file_path) as src:
            # Print raster information for debugging
            logger.info(f"Raster shape: {src.shape}")
            logger.info(f"Raster bands: {src.count}")
            
            # Read the data
            sar_data = src.read(1)  # Read the first band
            
            # Apply preprocessing steps
            # 1. Convert to decibels
            sar_db = 10 * np.log10(sar_data + 1e-10)  # Add small constant to avoid log(0)
            
            # 2. Apply speckle filtering (Lee filter)
            sar_filtered = _lee_filter(sar_db, size=5)
            
            # 3. Normalize the data
            sar_normalized = (sar_filtered - np.min(sar_filtered)) / (np.max(sar_filtered) - np.min(sar_filtered))
            
            return sar_normalized
    except RasterioIOError as e:
        logger.error(f"Rasterio IO Error: {e}")
        logger.error("This might be because the file is not a valid raster format or requires additional preprocessing.")
        return None
    except Exception as e:
        logger.error(f"Error preprocessing SAR data: {e}")
        logger.error(traceback.format_exc())
        return None

def detect_subsurface_features(sar_data: np.ndarray, threshold: float = 0.7) -> Optional[np.ndarray]:
    """Detect potential subsurface features in the SAR data."""
    try:
        # 1. Apply edge detection
        edges = ndimage.sobel(sar_data)
        
        # 2. Apply thresholding to identify strong edges
        edge_threshold = np.max(edges) * threshold
        strong_edges = edges > edge_threshold
        
        # 3. Apply morphological operations to connect edges
        connected_edges = ndimage.binary_closing(strong_edges, structure=np.ones((3, 3)))
        
        # 4. Remove small objects (noise)
        cleaned_features = ndimage.binary_opening(connected_edges, structure=np.ones((2, 2)))
        
        return cleaned_features
    except Exception as e:
        logger.error(f"Error detecting subsurface features: {e}")
        return None