from setuptools import setup, find_packages

setup(
    name="sentinel_sar",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'sentinelsat',
        'rasterio',
        'numpy',
        'matplotlib',
        'scipy',
        'geopandas',
        'shapely',
        'python-dotenv'
    ]
)