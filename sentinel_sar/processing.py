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

def search_sar_data(analyzer, footprint: str, start_date: str, end_date: str, platform_name: str = 'Sentinel-1') -> Dict:
    """Search for SAR data within the specified parameters."""
    try:
        # Check if API is authenticated
        if analyzer.api is None:
            logger.error("API not authenticated. Call authenticate() first.")
            return {}
            
        # Convert string dates to datetime objects
        start = datetime.datetime.strptime(start_date, '%Y%m%d').date()
        end = datetime.datetime.strptime(end_date, '%Y%m%d').date()
        
        # Log connection attempt
        logger.info(f"Attempting to connect to Copernicus Open Access Hub at {analyzer.api.api_url}")
        logger.info(f"Search parameters: footprint={footprint[:50]}..., date=({start} to {end}), platform={platform_name}")
        
        # Search for products
        analyzer.products = analyzer.api.query(
            footprint,
            date=(start, end),
            platformname=platform_name,
            producttype='SLC',  # Single Look Complex - best for subsurface analysis
            orbitdirection='ASCENDING'
        )
        
        logger.info(f"Found {len(analyzer.products)} products")
        return analyzer.products
    except Exception as e:
        logger.error(f"Error searching for data: {e}")
        # Add more detailed error information
        logger.debug(f"Detailed error: {traceback.format_exc()}")
        
        # Add connection troubleshooting information
        # logger.info("Connection troubleshooting:")
        # logger.info("1. Check your internet connection")
        # logger.info("2. Verify that the Copernicus Open Access Hub is accessible (https://scihub.copernicus.eu/dhus/)")
        # logger.info("3. Ensure your credentials are correct")
        # logger.info("4. The service might be temporarily unavailable or under maintenance")
        
        return {}

def search_cosmo_data(analyzer, footprint: str, start_date: str, end_date: str) -> Dict:
    """Search for COSMO-SkyMed SAR data within the specified parameters."""
    try:
        # Check if API token is available
        if not analyzer.cosmo_api_token:
            logger.error("COSMO-SkyMed API not authenticated. Call authenticate_cosmo() first.")
            return {}
            
        # Convert string dates to datetime objects
        start = datetime.datetime.strptime(start_date, '%Y%m%d').date()
        end = datetime.datetime.strptime(end_date, '%Y%m%d').date()
        
        # Log connection attempt
        logger.info(f"Searching for COSMO-SkyMed data")
        logger.info(f"Search parameters: footprint={footprint[:50]}..., date=({start} to {end})")
        
        # Construct the search API URL
        search_url = "https://api.registration.cosmo-skymed.it/products/search"
        
        # Create the search payload
        payload = {
            "dateRange": {
                "startDate": start.strftime("%Y-%m-%d"),
                "endDate": end.strftime("%Y-%m-%d")
            },
            "footprint": footprint,
            "productType": "SCS",  # Single-look Complex Slant - equivalent to Sentinel's SLC
            "maxResults": 100
        }
        
        # Set up the headers with the authentication token
        headers = {
            "Authorization": f"Bearer {analyzer.cosmo_api_token}",
            "Content-Type": "application/json"
        }
        
        # Make the search request
        response = requests.post(search_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            products_data = response.json()
            analyzer.products = products_data.get('products', {})
            # Make sure analyzer.products is not None before using len()
            product_count = len(analyzer.products) if analyzer.products is not None else 0
            logger.info(f"Found {product_count} COSMO-SkyMed products")
            return analyzer.products or {}  # Return empty dict if analyzer.products is None
        else:
            logger.error(f"Search failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return {}
            
    except Exception as e:
        logger.error(f"Error searching for COSMO-SkyMed data: {e}")
        logger.debug(f"Detailed error: {traceback.format_exc()}")
        
        # Add connection troubleshooting information
        # logger.info("Connection troubleshooting:")
        # logger.info("1. Check your internet connection")
        # logger.info("2. Verify that the COSMO-SkyMed API is accessible")
        # logger.info("3. Ensure your credentials are correct")
        # logger.info("4. The service might be temporarily unavailable or under maintenance")
        
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
            
        # Sort products by ingestion date
        products_df = analyzer.api.to_dataframe(analyzer.products)
        products_df_sorted = products_df.sort_values('ingestiondate', ascending=False)
        
        # Select the most recent products up to the limit
        products_to_download = products_df_sorted.head(limit)
        product_ids = products_to_download.index.tolist()
        
        # Download the products
        downloaded_products = analyzer.api.download_all(
            product_ids,
            directory_path=str(analyzer.download_path)
        )
        
        # Extract the actual file paths from the downloaded products
        file_paths = []
        # Handle the ResultTuple object correctly
        for product_info in downloaded_products:
            if hasattr(product_info, 'path') and os.path.exists(product_info.path):
                file_paths.append(product_info.path)
                logger.info(f"Successfully downloaded: {product_info.path}")
            else:
                logger.warning(f"Could not find path for product")
        
        return file_paths
    except Exception as e:
        logger.error(f"Error downloading products: {e}")
        return []

def download_cosmo_products(analyzer, limit: int = 1) -> List[str]:
    """Download the found COSMO-SkyMed products."""
    if not analyzer.products or len(analyzer.products) == 0:
        logger.warning("No COSMO-SkyMed products to download. Run search_cosmo_data first.")
        return []
    
    try:
        # Check if API token is available
        if not analyzer.cosmo_api_token:
            logger.error("COSMO-SkyMed API not authenticated. Call authenticate_cosmo() first.")
            return []
        
        # Sort products by acquisition date (newest first)
        sorted_products = sorted(
            analyzer.products, 
            key=lambda x: x.get('acquisitionDate', ''), 
            reverse=True
        )
        
        # Select the most recent products up to the limit
        products_to_download = sorted_products[:limit]
        
        file_paths = []
        for product in products_to_download:
            product_id = product.get('id')
            if not product_id:
                logger.warning("Product ID not found, skipping")
                continue
            
            # Construct the download URL
            download_url = f"https://api.registration.cosmo-skymed.it/products/{product_id}/download"
            
            # Set up the headers with the authentication token
            headers = {
                "Authorization": f"Bearer {analyzer.cosmo_api_token}"
            }
            
            # Make the download request
            logger.info(f"Downloading COSMO-SkyMed product {product_id}...")
            response = requests.get(download_url, headers=headers, stream=True)
            
            if response.status_code == 200:
                # Get the filename from the response headers or use the product ID
                filename = response.headers.get('Content-Disposition', '').split('filename=')[-1].strip('"') or f"{product_id}.zip"
                file_path = analyzer.download_path / filename
                
                # Download the file in chunks
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"Successfully downloaded: {file_path}")
                file_paths.append(str(file_path))
            else:
                logger.error(f"Download failed with status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
        
        return file_paths
        
    except Exception as e:
        logger.error(f"Error downloading COSMO-SkyMed products: {e}")
        return []

def process_sentinel1_data(analyzer, file_path: str) -> Optional[str]:
    """Process Sentinel-1 specific data format."""
    try:
        logger.info(f"Processing Sentinel-1 data: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error processing Sentinel-1 data: {e}")
        return None

def process_cosmo_data(analyzer, file_path: str) -> Optional[str]:
    """Process COSMO-SkyMed specific data format."""
    try:
        logger.info(f"Processing COSMO-SkyMed data: {file_path}")
        
        # Use utility function to extract zip file
        from sentinel_sar.utils import extract_zip_file, find_files_by_extension
        
        # Extract the zip file
        extract_dir = extract_zip_file(file_path, str(analyzer.download_path / 'extracted'))
        
        if not extract_dir:
            logger.error("Failed to extract the zip file")
            return None
        
        # Find the main SAR data file (typically with .h5 extension for COSMO-SkyMed)
        sar_files = find_files_by_extension(extract_dir, '.h5')
        
        if not sar_files:
            logger.error("No SAR data files found in the extracted archive")
            return None
        
        # Return the path to the first SAR file
        return sar_files[0]
    except Exception as e:
        logger.error(f"Error processing COSMO-SkyMed data: {e}")
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