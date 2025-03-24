# Sentinel SAR Data Analysis Tool

This tool fetches and analyzes Synthetic Aperture Radar (SAR) data from the Copernicus Open Access Hub to detect potential subsurface features. It's designed to assist in archaeological research by identifying anomalies that might indicate buried structures or artifacts.

## Features

- Fetch SAR data from Copernicus based on geographical coordinates
- Process and analyze SAR imagery to detect subsurface anomalies
- Visualize results with original data, processed data, and detected features
- Save analysis results as high-resolution images

## Requirements

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

1. Run the script:

```bash
python sentinel_sar_analysis.py
```

2. Enter your Copernicus Open Access Hub credentials when prompted
3. Specify the area of interest by entering coordinates (or use the default Giza, Egypt coordinates)
4. Enter the date range for SAR data acquisition
5. The script will download and analyze the data, then display and save the results

## Example

The default coordinates are set to the Giza Plateau in Egypt, which is known for its archaeological significance. The script will search for SAR data in this area and analyze it to detect potential subsurface features.

## Notes

- You need a registered account at the [Copernicus Open Access Hub](https://scihub.copernicus.eu/)
- The script downloads SAR data which can be large files (several GB)
- Processing SAR data is computationally intensive and may take time depending on your hardware
- The results are saved in a 'data' directory created in the current working directory