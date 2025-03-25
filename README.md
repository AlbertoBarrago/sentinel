# Sentinel SAR Analysis Tool

A Python tool for fetching and analyzing Synthetic Aperture Radar (SAR) data from Copernicus Sentinel-1. This tool allows for data acquisition based on coordinates, processing the imagery, and applying signal processing techniques to detect subsurface anomalies.

## Features

- Fetch SAR data from Copernicus Open Access Hub or Copernicus Data Space Ecosystem

- Define areas of interest using geographic coordinates
- Download and process SAR imagery
- Apply preprocessing techniques including speckle filtering
- Detect potential subsurface features using edge detection and morphological operations
- Visualize results with original data, processed data, and detected features


## How to obtain API_KEY from copernicus
``` bash
export KEYCLOAK_TOKEN=$(curl -s -X POST -H "Content-Type: application/x-www-form-urlencoded" \
  --data 'client_id=<client_id>' \
  --data 'client_secret=<client_secret>' \
  --data 'grant_type=client_credentials' \
  'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token' | jq -r .access_token)
```

## Installation
You can use setup.py 
```bash
python setup.py install
```
or
```bash
pip install -r requirements.txt
```

### Prerequisites

- Python 3.7+
- pip (Python package installer)

### Setup

1. Clone this repository:
```bash
git clone https://github.com/yourusername/sentinel-sar-analysis.git
cd sentinel-sar-analysis
```

2. Set up a virtual environment (recommended):

   **Using venv** (Python's built-in virtual environment):
   ```bash
   # Create a virtual environment
   python3 -m venv .venv
   
   # Activate the virtual environment
   # On macOS/Linux:
   source .venv/bin/activate
   # On Windows:
   # .venv\Scripts\activate
   ```

   **Using conda** (if you prefer Anaconda/Miniconda):
   ```bash
   # Create a conda environment
   conda create -n sentinel-env python=3.9
   
   # Activate the conda environment
   conda activate sentinel-env
   ```

3. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables (optional):

   Create a `.env` file in the project root directory with your Copernicus credentials:
   ```
   CLIENT_ID=your_copernicus_client_id
   CLIENT_SECRET=your_copernicus_client_secret
   API_URL=https://catalogue.dataspace.copernicus.eu/api/hub
   ```
   
   This step is optional but recommended if you plan to use the example script.

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


- You need a registered account at the [Copernicus Open Access Hub](https://dataspace.copernicus.eu/)
- The script downloads SAR data which can be large files (several GB)
- Processing SAR data is computationally intensive and may take time depending on your hardware
- The results are saved in a 'data' directory created in the current working directory