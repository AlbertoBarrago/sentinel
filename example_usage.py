#!/usr/bin/env python3
"""
Example usage of the Sentinel SAR Analysis Tool

This script demonstrates how to use the SARAnalyzer class to analyze
SAR data for a specific area of interest.
"""

from sentinel_sar_analysis import SARAnalyzer

def main():
    # Create an instance of the SARAnalyzer
    analyzer = SARAnalyzer()
    
    # Define the area of interest (Giza, Egypt)
    min_lon = 31.0
    min_lat = 29.9
    max_lon = 31.2
    max_lat = 30.1
    
    # Define the date range (last 6 months)
    start_date = "20230101"
    end_date = "20231231"
    
    # Run the analysis
    print("Starting analysis for the Giza Plateau region...")
    analyzer.analyze_area(min_lon, min_lat, max_lon, max_lat, start_date, end_date)

if __name__ == "__main__":
    main()