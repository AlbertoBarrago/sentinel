"""
Visualization functions for SAR data.
"""

import logging
import numpy as np
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

def visualize_results(analyzer, original_data: np.ndarray, processed_data: np.ndarray, 
                      features: np.ndarray, title: str = "SAR Analysis Results") -> None:
    """Visualize the original data, processed data, and detected features."""
    try:
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        # Plot original data
        axes[0].imshow(original_data, cmap='gray')
        axes[0].set_title('Original SAR Data')
        axes[0].axis('off')
        
        # Plot processed data
        axes[1].imshow(processed_data, cmap='viridis')
        axes[1].set_title('Processed SAR Data')
        axes[1].axis('off')
        
        # Plot detected features
        axes[2].imshow(processed_data, cmap='gray')
        axes[2].imshow(features, cmap='hot', alpha=0.5)
        axes[2].set_title('Detected Subsurface Features')
        axes[2].axis('off')
        
        plt.suptitle(title)
        plt.tight_layout()
        
        # Save the figure
        output_path = analyzer.download_path / 'sar_analysis_results.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Results saved to {output_path}")
        
        # Show the figure
        plt.show()
        
    except Exception as e:
        logger.error(f"Error visualizing results: {e}")

def visualize_time_series(analyzer, time_series_data: list, dates: list, title: str = "SAR Time Series Analysis") -> None:
    """Visualize a time series of SAR data to detect changes over time."""
    try:
        n_images = len(time_series_data)
        if n_images == 0:
            logger.error("No time series data to visualize")
            return
            
        # Determine the grid layout based on the number of images
        cols = min(4, n_images)
        rows = (n_images + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=(cols * 5, rows * 5))
        if rows == 1 and cols == 1:
            axes = np.array([axes])
        axes = axes.flatten()
        
        # Plot each image in the time series
        for i, (data, date) in enumerate(zip(time_series_data, dates)):
            if i < len(axes):
                axes[i].imshow(data, cmap='viridis')
                axes[i].set_title(f'Date: {date}')
                axes[i].axis('off')
        
        # Hide any unused subplots
        for i in range(n_images, len(axes)):
            axes[i].axis('off')
            
        plt.suptitle(title)
        plt.tight_layout()
        
        # Save the figure
        output_path = analyzer.download_path / 'sar_time_series_results.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Time series results saved to {output_path}")
        
        # Show the figure
        plt.show()
        
    except Exception as e:
        logger.error(f"Error visualizing time series: {e}")

def visualize_change_detection(analyzer, before_data: np.ndarray, after_data: np.ndarray, 
                              difference: np.ndarray, title: str = "SAR Change Detection") -> None:
    """Visualize before and after SAR data with highlighted changes."""
    try:
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        # Plot before data
        axes[0].imshow(before_data, cmap='gray')
        axes[0].set_title('Before')
        axes[0].axis('off')
        
        # Plot after data
        axes[1].imshow(after_data, cmap='gray')
        axes[1].set_title('After')
        axes[1].axis('off')
        
        # Plot difference with threshold
        # Normalize difference for better visualization
        norm_diff = (difference - np.min(difference)) / (np.max(difference) - np.min(difference))
        axes[2].imshow(norm_diff, cmap='RdBu_r')
        axes[2].set_title('Change Detection')
        axes[2].axis('off')
        
        plt.suptitle(title)
        plt.tight_layout()
        
        # Save the figure
        output_path = analyzer.download_path / 'sar_change_detection_results.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Change detection results saved to {output_path}")
        
        # Show the figure
        plt.show()
        
    except Exception as e:
        logger.error(f"Error visualizing change detection: {e}")

def create_interactive_map(analyzer, sar_data: np.ndarray, geotransform, crs, 
                          title: str = "Interactive SAR Data Map") -> None:
    """Create an interactive map of the SAR data with geographic coordinates."""
    try:
        # This function requires additional libraries like folium
        # Check if folium is installed
        try:
            import folium
            from folium import plugins
            import rasterio
            from rasterio.transform import from_origin
            from sentinel_sar.utils import normalize_array
        except ImportError:
            logger.error("This function requires folium and rasterio. Install with: pip install folium rasterio")
            return
            
        # Get the bounds of the data
        height, width = sar_data.shape
        west, north = geotransform[0], geotransform[3]
        east = west + width * geotransform[1]
        south = north + height * geotransform[5]  # Note: geotransform[5] is typically negative
        
        # Create a centered map
        center_lat = (north + south) / 2
        center_lon = (east + west) / 2
        map_obj = folium.Map(location=[center_lat, center_lon], zoom_start=10)
        
        # Add the SAR data as an overlay - use utility function for normalization
        img_data = normalize_array(sar_data.copy()) * 255
        img_data = img_data.astype(np.uint8)
        
        # Add the image overlay
        from folium.raster_layers import ImageOverlay
        ImageOverlay(
            image=img_data,
            bounds=[[south, west], [north, east]],
            opacity=0.7,
            name="SAR Data"
        ).add_to(map_obj)
        
        # Add layer control
        folium.LayerControl().add_to(map_obj)
        
        # Save the map
        output_path = analyzer.download_path / 'sar_interactive_map.html'
        map_obj.save(str(output_path))
        logger.info(f"Interactive map saved to {output_path}")
        
    except Exception as e:
        logger.error(f"Error creating interactive map: {e}")