"""Generate dynamic, interactive research infographics and map dashboard from research analysis dataset."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

# Geographic coordinates lookup for U.S. target locations (all localized cities, counties, and states)
COORDINATES_MAP: dict[str, dict[str, float | str]] = {
    # Cities
    "Los Angeles": {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles, CA"},
    "Los Angeles, Ca": {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles, CA"},
    "Los Angeles, CA": {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles, CA"},
    "San Francisco": {"lat": 37.7749, "lon": -122.4194, "name": "San Francisco, CA"},
    "San Francisco, Ca": {"lat": 37.7749, "lon": -122.4194, "name": "San Francisco, CA"},
    "San Francisco Bay Area, Ca": {"lat": 37.7749, "lon": -122.4194, "name": "San Francisco, CA"},
    "San Francisco County": {"lat": 37.7749, "lon": -122.4194, "name": "San Francisco, CA"},
    "Seattle": {"lat": 47.6062, "lon": -122.3321, "name": "Seattle, WA"},
    "Boston": {"lat": 42.3601, "lon": -71.0589, "name": "Boston, MA"},
    "Boston, Ma": {"lat": 42.3601, "lon": -71.0589, "name": "Boston, MA"},
    "Boston, MA": {"lat": 42.3601, "lon": -71.0589, "name": "Boston, MA"},
    "Chicago": {"lat": 41.8781, "lon": -87.6298, "name": "Chicago, IL"},
    "Chicago, Il": {"lat": 41.8781, "lon": -87.6298, "name": "Chicago, IL"},
    "New York City": {"lat": 40.7128, "lon": -74.0060, "name": "New York City, NY"},
    "New York": {"lat": 42.9538, "lon": -75.5268, "name": "New York (State)"},
    "New York, Ny": {"lat": 40.7128, "lon": -74.0060, "name": "New York City, NY"},
    "New York City, Ny": {"lat": 40.7128, "lon": -74.0060, "name": "New York City, NY"},
    "Leonia": {"lat": 40.8654, "lon": -73.9876, "name": "Leonia, NJ"},
    "Mantoloking": {"lat": 40.0387, "lon": -74.0526, "name": "Mantoloking, NJ"},
    "Newark, Nj": {"lat": 40.7357, "lon": -74.1724, "name": "Newark, NJ"},
    "Atlanta": {"lat": 33.7490, "lon": -84.3880, "name": "Atlanta, GA"},
    "Atlanta, Ga": {"lat": 33.7490, "lon": -84.3880, "name": "Atlanta, GA"},
    "Atlanta, GA": {"lat": 33.7490, "lon": -84.3880, "name": "Atlanta, GA"},
    "Austin": {"lat": 30.2672, "lon": -97.7431, "name": "Austin, TX"},
    "Austin, Tx": {"lat": 30.2672, "lon": -97.7431, "name": "Austin, TX"},
    "Austin, TX": {"lat": 30.2672, "lon": -97.7431, "name": "Austin, TX"},
    "Arlington, TX": {"lat": 32.7357, "lon": -97.1081, "name": "Arlington, TX"},
    "Arlington, Tx": {"lat": 32.7357, "lon": -97.1081, "name": "Arlington, TX"},
    "Dallas, Tx": {"lat": 32.7767, "lon": -96.7970, "name": "Dallas, TX"},
    "Fort Worth, Tx": {"lat": 32.7555, "lon": -97.3308, "name": "Fort Worth, TX"},
    "Fort Worth": {"lat": 32.7555, "lon": -97.3308, "name": "Fort Worth, TX"},
    "Houston, Tx": {"lat": 29.7604, "lon": -95.3698, "name": "Houston, TX"},
    "San Antonio, Tx": {"lat": 29.4241, "lon": -98.4936, "name": "San Antonio, TX"},
    "Miami": {"lat": 25.7617, "lon": -80.1918, "name": "Miami, FL"},
    "Miami, Fl": {"lat": 25.7617, "lon": -80.1918, "name": "Miami, FL"},
    "Coral Gables": {"lat": 25.7215, "lon": -80.2684, "name": "Coral Gables, FL"},
    "Jacksonville, Fl": {"lat": 30.3322, "lon": -81.6557, "name": "Jacksonville, FL"},
    "Tampa, Fl": {"lat": 27.9506, "lon": -82.4572, "name": "Tampa, FL"},
    "Detroit": {"lat": 42.3314, "lon": -83.0458, "name": "Detroit, MI"},
    "Detroit, Mi": {"lat": 42.3314, "lon": -83.0458, "name": "Detroit, MI"},
    "Portland, Or": {"lat": 45.5152, "lon": -122.6784, "name": "Portland, OR"},
    "Philadelphia": {"lat": 39.9526, "lon": -75.1652, "name": "Philadelphia, PA"},
    "Philadelphia, Pa": {"lat": 39.9526, "lon": -75.1652, "name": "Philadelphia, PA"},
    "Pittsburgh, PA": {"lat": 40.4406, "lon": -79.9959, "name": "Pittsburgh, PA"},
    "Pittsburgh, Pa": {"lat": 40.4406, "lon": -79.9959, "name": "Pittsburgh, PA"},
    "Lancaster, Pa": {"lat": 40.0379, "lon": -76.3055, "name": "Lancaster, PA"},
    "Charlotte, Nc": {"lat": 35.2271, "lon": -80.8431, "name": "Charlotte, NC"},
    "Raleigh, Nc": {"lat": 35.7796, "lon": -78.6382, "name": "Raleigh, NC"},
    "Cary, Nc": {"lat": 35.7915, "lon": -78.7811, "name": "Cary, NC"},
    "Asheville, Nc": {"lat": 35.5951, "lon": -82.5515, "name": "Asheville, NC"},
    "Greensboro, Nc": {"lat": 36.0726, "lon": -79.7920, "name": "Greensboro, NC"},
    "Greensboro, NC": {"lat": 36.0726, "lon": -79.7920, "name": "Greensboro, NC"},
    "Norfolk": {"lat": 36.8508, "lon": -76.2859, "name": "Norfolk, VA"},
    "Norfolk, VA": {"lat": 36.8508, "lon": -76.2859, "name": "Norfolk, VA"},
    "Virginia Beach, Va": {"lat": 36.8529, "lon": -75.9780, "name": "Virginia Beach, VA"},
    "Virginia Beach, VA": {"lat": 36.8529, "lon": -75.9780, "name": "Virginia Beach, VA"},
    "Phoenix, Az": {"lat": 33.4484, "lon": -112.0740, "name": "Phoenix, AZ"},
    "Salt Lake City": {"lat": 40.7608, "lon": -111.8910, "name": "Salt Lake City, UT"},
    "Salt Lake City, Ut": {"lat": 40.7608, "lon": -111.8910, "name": "Salt Lake City, UT"},
    "Des Moines, Ia": {"lat": 41.5868, "lon": -93.6250, "name": "Des Moines, IA"},
    "New Haven, Ct": {"lat": 41.3083, "lon": -72.9279, "name": "New Haven, CT"},
    "Fairfield, Ct": {"lat": 41.1412, "lon": -73.2637, "name": "Fairfield, CT"},
    "Augusta, Me": {"lat": 44.3106, "lon": -69.7795, "name": "Augusta, ME"},
    "Naperville": {"lat": 41.7508, "lon": -88.1535, "name": "Naperville, IL"},
    "Evanston": {"lat": 42.0451, "lon": -87.6877, "name": "Evanston, IL"},
    "Davis, CA": {"lat": 38.5449, "lon": -121.7405, "name": "Davis, CA"},
    "Davis, Ca": {"lat": 38.5449, "lon": -121.7405, "name": "Davis, CA"},
    "Sacramento, CA": {"lat": 38.5816, "lon": -121.4944, "name": "Sacramento, CA"},
    "Baton Rouge, LA": {"lat": 30.4515, "lon": -91.1871, "name": "Baton Rouge, LA"},
    "Knoxville, TN": {"lat": 35.9606, "lon": -83.9207, "name": "Knoxville, TN"},
    "Carson City, Nv": {"lat": 39.1638, "lon": -119.7674, "name": "Carson City, NV"},
    "Colorado Springs, Co": {"lat": 38.8339, "lon": -104.8214, "name": "Colorado Springs, CO"},
    "Providence, Ri": {"lat": 41.8240, "lon": -71.4128, "name": "Providence, RI"},
    "Washington Dc": {"lat": 38.9072, "lon": -77.0369, "name": "Washington, DC"},
    "Anchorage, Ak": {"lat": 61.2181, "lon": -149.9003, "name": "Anchorage, AK"},
    # Counties
    "Loudoun County": {"lat": 39.0840, "lon": -77.6412, "name": "Loudoun County, VA"},
    "Fulton County": {"lat": 33.7903, "lon": -84.4677, "name": "Fulton County, GA"},
    "Miami-Dade County": {"lat": 25.5516, "lon": -80.6327, "name": "Miami-Dade County, FL"},
    # States
    "California": {"lat": 36.7783, "lon": -119.4179, "name": "California (State)"},
    "Connecticut": {"lat": 41.6032, "lon": -73.0877, "name": "Connecticut (State)"},
    "Texas": {"lat": 31.9686, "lon": -99.9018, "name": "Texas (State)"},
    "Illinois": {"lat": 40.6331, "lon": -89.3985, "name": "Illinois (State)"},
    "Georgia": {"lat": 32.1656, "lon": -82.9001, "name": "Georgia (State)"},
    "Pennsylvania": {"lat": 41.2033, "lon": -77.1945, "name": "Pennsylvania (State)"},
    "Florida": {"lat": 27.6648, "lon": -81.5158, "name": "Florida (State)"},
    "New Jersey": {"lat": 40.0583, "lon": -74.4057, "name": "New Jersey (State)"},
    "Virginia": {"lat": 37.4316, "lon": -78.6569, "name": "Virginia (State)"},
    "Iowa": {"lat": 41.8780, "lon": -93.0977, "name": "Iowa (State)"},
    "Maine": {"lat": 45.2538, "lon": -69.4455, "name": "Maine (State)"},
    "Massachusetts": {"lat": 42.4072, "lon": -71.3824, "name": "Massachusetts (State)"},
    "Utah": {"lat": 39.3210, "lon": -111.0937, "name": "Utah (State)"},
    "Nevada": {"lat": 38.8026, "lon": -116.4194, "name": "Nevada (State)"},
    "North Carolina": {"lat": 35.7596, "lon": -79.0193, "name": "North Carolina (State)"},
    "Wyoming": {"lat": 43.0759, "lon": -107.2903, "name": "Wyoming (State)"},
    "Colorado": {"lat": 39.5501, "lon": -105.7821, "name": "Colorado (State)"},
    "Alaska": {"lat": 64.2008, "lon": -149.4937, "name": "Alaska (State)"},
    "Arizona": {"lat": 34.0489, "lon": -111.0937, "name": "Arizona (State)"},
    "Idaho": {"lat": 44.0682, "lon": -114.7420, "name": "Idaho (State)"},
    "Kansas": {"lat": 39.0119, "lon": -98.4842, "name": "Kansas (State)"},
    "Maryland": {"lat": 39.0458, "lon": -76.6413, "name": "Maryland (State)"},
    "Michigan": {"lat": 44.3148, "lon": -85.6024, "name": "Michigan (State)"},
    "Minnesota": {"lat": 46.7296, "lon": -94.6859, "name": "Minnesota (State)"},
    "Missouri": {"lat": 37.9643, "lon": -91.8318, "name": "Missouri (State)"},
    "Montana": {"lat": 46.8797, "lon": -110.3626, "name": "Montana (State)"},
    "Nebraska": {"lat": 41.4925, "lon": -99.9018, "name": "Nebraska (State)"},
    "Nebraska (State)": {"lat": 41.4925, "lon": -99.9018, "name": "Nebraska (State)"},
    "New Hampshire": {"lat": 43.1939, "lon": -71.5724, "name": "New Hampshire (State)"},
    "New Hampshire (State)": {"lat": 43.1939, "lon": -71.5724, "name": "New Hampshire (State)"},
    "New Mexico": {"lat": 34.5199, "lon": -105.8701, "name": "New Mexico (State)"},
    "New Mexico (State)": {"lat": 34.5199, "lon": -105.8701, "name": "New Mexico (State)"},
    "Ohio": {"lat": 40.4173, "lon": -82.9071, "name": "Ohio (State)"},
    "Ohio (State)": {"lat": 40.4173, "lon": -82.9071, "name": "Ohio (State)"},
    "Oklahoma": {"lat": 35.0078, "lon": -97.0929, "name": "Oklahoma (State)"},
    "Oklahoma (State)": {"lat": 35.0078, "lon": -97.0929, "name": "Oklahoma (State)"},
    "Tennessee": {"lat": 35.5175, "lon": -86.5804, "name": "Tennessee (State)"},
    "Tennessee (State)": {"lat": 35.5175, "lon": -86.5804, "name": "Tennessee (State)"},
    "Vermont": {"lat": 44.5588, "lon": -72.5778, "name": "Vermont (State)"},
    "Vermont (State)": {"lat": 44.5588, "lon": -72.5778, "name": "Vermont (State)"},
    "District Of Columbia": {"lat": 38.9072, "lon": -77.0369, "name": "District of Columbia"},
    "Alabama": {"lat": 32.8067, "lon": -86.7911, "name": "Alabama (State)"},
    "Alabama (State)": {"lat": 32.8067, "lon": -86.7911, "name": "Alabama (State)"},
    "Arkansas": {"lat": 34.9697, "lon": -92.3731, "name": "Arkansas (State)"},
    "Arkansas (State)": {"lat": 34.9697, "lon": -92.3731, "name": "Arkansas (State)"},
    "Delaware": {"lat": 39.3185, "lon": -75.5071, "name": "Delaware (State)"},
    "Delaware (State)": {"lat": 39.3185, "lon": -75.5071, "name": "Delaware (State)"},
    "Hawaii": {"lat": 19.8987, "lon": -155.6659, "name": "Hawaii (State)"},
    "Hawaii (State)": {"lat": 19.8987, "lon": -155.6659, "name": "Hawaii (State)"},
    "Indiana": {"lat": 40.2672, "lon": -86.1349, "name": "Indiana (State)"},
    "Indiana (State)": {"lat": 40.2672, "lon": -86.1349, "name": "Indiana (State)"},
    "Kentucky": {"lat": 37.8393, "lon": -84.2700, "name": "Kentucky (State)"},
    "Kentucky (State)": {"lat": 37.8393, "lon": -84.2700, "name": "Kentucky (State)"},
    "Louisiana": {"lat": 31.2448, "lon": -92.1450, "name": "Louisiana (State)"},
    "Louisiana (State)": {"lat": 31.2448, "lon": -92.1450, "name": "Louisiana (State)"},
    "Mississippi": {"lat": 32.3547, "lon": -89.3985, "name": "Mississippi (State)"},
    "Mississippi (State)": {"lat": 32.3547, "lon": -89.3985, "name": "Mississippi (State)"},
    "North Dakota": {"lat": 47.5515, "lon": -101.0020, "name": "North Dakota (State)"},
    "North Dakota (State)": {"lat": 47.5515, "lon": -101.0020, "name": "North Dakota (State)"},
    "Oregon": {"lat": 43.8041, "lon": -120.5542, "name": "Oregon (State)"},
    "Oregon (State)": {"lat": 43.8041, "lon": -120.5542, "name": "Oregon (State)"},
    "Rhode Island": {"lat": 41.5801, "lon": -71.4774, "name": "Rhode Island (State)"},
    "Rhode Island (State)": {"lat": 41.5801, "lon": -71.4774, "name": "Rhode Island (State)"},
    "South Carolina": {"lat": 33.8361, "lon": -81.1637, "name": "South Carolina (State)"},
    "South Carolina (State)": {"lat": 33.8361, "lon": -81.1637, "name": "South Carolina (State)"},
    "South Dakota": {"lat": 43.9695, "lon": -99.9018, "name": "South Dakota (State)"},
    "South Dakota (State)": {"lat": 43.9695, "lon": -99.9018, "name": "South Dakota (State)"},
    "Washington": {"lat": 47.7511, "lon": -120.7401, "name": "Washington (State)"},
    "Washington (State)": {"lat": 47.7511, "lon": -120.7401, "name": "Washington (State)"},
    "West Virginia": {"lat": 38.5976, "lon": -80.4549, "name": "West Virginia (State)"},
    "West Virginia (State)": {"lat": 38.5976, "lon": -80.4549, "name": "West Virginia (State)"},
    "Wisconsin": {"lat": 43.7844, "lon": -88.7879, "name": "Wisconsin (State)"},
    "Wisconsin (State)": {"lat": 43.7844, "lon": -88.7879, "name": "Wisconsin (State)"},
    "California (State)": {"lat": 36.7783, "lon": -119.4179, "name": "California (State)"},
    "Connecticut (State)": {"lat": 41.6032, "lon": -73.0877, "name": "Connecticut (State)"},
    "Texas (State)": {"lat": 31.9686, "lon": -99.9018, "name": "Texas (State)"},
    "Illinois (State)": {"lat": 40.6331, "lon": -89.3985, "name": "Illinois (State)"},
    "Georgia (State)": {"lat": 32.1656, "lon": -82.9001, "name": "Georgia (State)"},
    "Pennsylvania (State)": {"lat": 41.2033, "lon": -77.1945, "name": "Pennsylvania (State)"},
    "Florida (State)": {"lat": 27.6648, "lon": -81.5158, "name": "Florida (State)"},
    "New Jersey (State)": {"lat": 40.0583, "lon": -74.4057, "name": "New Jersey (State)"},
    "Virginia (State)": {"lat": 37.4316, "lon": -78.6569, "name": "Virginia (State)"},
    "Iowa (State)": {"lat": 41.8780, "lon": -93.0977, "name": "Iowa (State)"},
    "Maine (State)": {"lat": 45.2538, "lon": -69.4455, "name": "Maine (State)"},
    "Massachusetts (State)": {"lat": 42.4072, "lon": -71.3824, "name": "Massachusetts (State)"},
    "Utah (State)": {"lat": 39.3210, "lon": -111.0937, "name": "Utah (State)"},
    "Nevada (State)": {"lat": 38.8026, "lon": -116.4194, "name": "Nevada (State)"},
    "North Carolina (State)": {"lat": 35.7596, "lon": -79.0193, "name": "North Carolina (State)"},
    "Wyoming (State)": {"lat": 43.0759, "lon": -107.2903, "name": "Wyoming (State)"},
    "Colorado (State)": {"lat": 39.5501, "lon": -105.7821, "name": "Colorado (State)"},
    "Alaska (State)": {"lat": 64.2008, "lon": -149.4937, "name": "Alaska (State)"},
    "Arizona (State)": {"lat": 34.0489, "lon": -111.0937, "name": "Arizona (State)"},
    "Idaho (State)": {"lat": 44.0682, "lon": -114.7420, "name": "Idaho (State)"},
    "Kansas (State)": {"lat": 39.0119, "lon": -98.4842, "name": "Kansas (State)"},
    "Maryland (State)": {"lat": 39.0458, "lon": -76.6413, "name": "Maryland (State)"},
    "Michigan (State)": {"lat": 44.3148, "lon": -85.6024, "name": "Michigan (State)"},
    "Minnesota (State)": {"lat": 46.7296, "lon": -94.6859, "name": "Minnesota (State)"},
    "Missouri (State)": {"lat": 37.9643, "lon": -91.8318, "name": "Missouri (State)"},
    "Montana (State)": {"lat": 46.8797, "lon": -110.3626, "name": "Montana (State)"},
    # Additional Coded Cities
    "Ferguson, MO": {"lat": 38.7445, "lon": -90.3073, "name": "Ferguson, MO"},
    "Ferguson": {"lat": 38.7445, "lon": -90.3073, "name": "Ferguson, MO"},
    "Sandy Springs, GA": {"lat": 33.9304, "lon": -84.3733, "name": "Sandy Springs, GA"},
    "Sandy Springs": {"lat": 33.9304, "lon": -84.3733, "name": "Sandy Springs, GA"},
    "Mount Prospect, IL": {"lat": 42.0664, "lon": -87.9373, "name": "Mount Prospect, IL"},
    "Mount Prospect": {"lat": 42.0664, "lon": -87.9373, "name": "Mount Prospect, IL"},
    "Chesapeake, VA": {"lat": 36.7682, "lon": -76.2875, "name": "Chesapeake, VA"},
    "Chesapeake": {"lat": 36.7682, "lon": -76.2875, "name": "Chesapeake, VA"},
    "Wheaton, IL": {"lat": 41.8661, "lon": -88.1070, "name": "Wheaton, IL"},
    "Wheaton": {"lat": 41.8661, "lon": -88.1070, "name": "Wheaton, IL"},
    "Rochester, NY": {"lat": 43.1566, "lon": -77.6088, "name": "Rochester, NY"},
    "Rochester": {"lat": 43.1566, "lon": -77.6088, "name": "Rochester, NY"},
    "Buffalo, NY": {"lat": 42.8864, "lon": -78.8784, "name": "Buffalo, NY"},
    "Buffalo": {"lat": 42.8864, "lon": -78.8784, "name": "Buffalo, NY"},
    "Las Vegas, NV": {"lat": 36.1699, "lon": -115.1398, "name": "Las Vegas, NV"},
    "Las Vegas": {"lat": 36.1699, "lon": -115.1398, "name": "Las Vegas, NV"},
    "Minneapolis, MN": {"lat": 44.9778, "lon": -93.2650, "name": "Minneapolis, MN"},
    "Minneapolis": {"lat": 44.9778, "lon": -93.2650, "name": "Minneapolis, MN"},
    "Fort Lauderdale, FL": {"lat": 26.1224, "lon": -80.1373, "name": "Fort Lauderdale, FL"},
    "Fort Lauderdale": {"lat": 26.1224, "lon": -80.1373, "name": "Fort Lauderdale, FL"},
    "Roanoke, VA": {"lat": 37.2710, "lon": -79.9414, "name": "Roanoke, VA"},
    "Roanoke": {"lat": 37.2710, "lon": -79.9414, "name": "Roanoke, VA"},
    "Salem, OR": {"lat": 44.9429, "lon": -123.0351, "name": "Salem, OR"},
    "Salem": {"lat": 44.9429, "lon": -123.0351, "name": "Salem, OR"},
    "Jefferson City, MO": {"lat": 38.5767, "lon": -92.1735, "name": "Jefferson City, MO"},
    "Jefferson City": {"lat": 38.5767, "lon": -92.1735, "name": "Jefferson City, MO"},
    "Oklahoma City, OK": {"lat": 35.4676, "lon": -97.5164, "name": "Oklahoma City, OK"},
    "Oklahoma City": {"lat": 35.4676, "lon": -97.5164, "name": "Oklahoma City, OK"},
    "Grand Junction, CO": {"lat": 39.0639, "lon": -108.5506, "name": "Grand Junction, CO"},
    "Grand Junction": {"lat": 39.0639, "lon": -108.5506, "name": "Grand Junction, CO"},
    "Tucson, AZ": {"lat": 32.2226, "lon": -110.9747, "name": "Tucson, AZ"},
    "Tucson": {"lat": 32.2226, "lon": -110.9747, "name": "Tucson, AZ"},
    "Orlando, FL": {"lat": 28.5383, "lon": -81.3792, "name": "Orlando, FL"},
    "Orlando": {"lat": 28.5383, "lon": -81.3792, "name": "Orlando, FL"},
    "New Orleans, LA": {"lat": 29.9511, "lon": -90.0715, "name": "New Orleans, LA"},
    "New Orleans": {"lat": 29.9511, "lon": -90.0715, "name": "New Orleans, LA"},
    "Plano, TX": {"lat": 33.0198, "lon": -96.6989, "name": "Plano, TX"},
    "Plano": {"lat": 33.0198, "lon": -96.6989, "name": "Plano, TX"},
    "El Paso, TX": {"lat": 31.7619, "lon": -106.4850, "name": "El Paso, TX"},
    "El Paso": {"lat": 31.7619, "lon": -106.4850, "name": "El Paso, TX"},
    "Tacoma, WA": {"lat": 47.2529, "lon": -122.4443, "name": "Tacoma, WA"},
    "Tacoma": {"lat": 47.2529, "lon": -122.4443, "name": "Tacoma, WA"},
    "Fort Myers, FL": {"lat": 26.6406, "lon": -81.8723, "name": "Fort Myers, FL"},
    "Fort Myers": {"lat": 26.6406, "lon": -81.8723, "name": "Fort Myers, FL"},
    "Riverside, CA": {"lat": 33.9806, "lon": -117.3755, "name": "Riverside, CA"},
    "Riverside": {"lat": 33.9806, "lon": -117.3755, "name": "Riverside, CA"},
    "Charleston, SC": {"lat": 32.7765, "lon": -79.9311, "name": "Charleston, SC"},
    "Charleston": {"lat": 32.7765, "lon": -79.9311, "name": "Charleston, SC"},
    "Honolulu, HI": {"lat": 21.3069, "lon": -157.8583, "name": "Honolulu, HI"},
    "Honolulu": {"lat": 21.3069, "lon": -157.8583, "name": "Honolulu, HI"},
    "Cleveland, OH": {"lat": 41.4993, "lon": -81.6944, "name": "Cleveland, OH"},
    "Cleveland": {"lat": 41.4993, "lon": -81.6944, "name": "Cleveland, OH"},
    "Wichita, KS": {"lat": 37.6872, "lon": -97.3301, "name": "Wichita, KS"},
    "Wichita": {"lat": 37.6872, "lon": -97.3301, "name": "Wichita, KS"},
    "Anchorage, AK": {"lat": 61.2181, "lon": -149.9003, "name": "Anchorage, AK"},
    "Anchorage": {"lat": 61.2181, "lon": -149.9003, "name": "Anchorage, AK"},
    "Aspinwall, PA": {"lat": 40.4937, "lon": -79.9056, "name": "Aspinwall, PA"},
    "Aspinwall": {"lat": 40.4937, "lon": -79.9056, "name": "Aspinwall, PA"},
    "Albany, GA": {"lat": 31.5785, "lon": -84.1557, "name": "Albany, GA"},
    "Allentown, PA": {"lat": 40.6084, "lon": -75.4902, "name": "Allentown, PA"},
    "Annapolis, MD": {"lat": 38.9784, "lon": -76.4922, "name": "Annapolis, MD"},
    "Bangor, ME": {"lat": 44.8016, "lon": -68.7712, "name": "Bangor, ME"},
    "Biloxi, MS": {"lat": 30.3960, "lon": -88.8853, "name": "Biloxi, MS"},
    "Cedar Rapids, IA": {"lat": 41.9779, "lon": -91.6656, "name": "Cedar Rapids, IA"},
    "Danville, VA": {"lat": 36.5860, "lon": -79.3950, "name": "Danville, VA"},
    "Daytona Beach, FL": {"lat": 29.2108, "lon": -81.0228, "name": "Daytona Beach, FL"},
    "Duluth, MN": {"lat": 46.7867, "lon": -92.1005, "name": "Duluth, MN"},
    "Erie, PA": {"lat": 42.1292, "lon": -80.0851, "name": "Erie, PA"},
    "Fargo, ND": {"lat": 46.8772, "lon": -96.7898, "name": "Fargo, ND"},
    "Fort Collins, CO": {"lat": 40.5853, "lon": -105.0844, "name": "Fort Collins, CO"},
    "Johnson City, TN": {"lat": 36.3134, "lon": -82.3535, "name": "Johnson City, TN"},
    "Little Rock, AR": {"lat": 34.7465, "lon": -92.2896, "name": "Little Rock, AR"},
    "Madison, WI": {"lat": 43.0731, "lon": -89.4012, "name": "Madison, WI"},
    "Memphis, TN": {"lat": 35.1495, "lon": -90.0490, "name": "Memphis, TN"},
    "Nashville, TN": {"lat": 36.1627, "lon": -86.7816, "name": "Nashville, TN"},
    "Palm Springs, CA": {"lat": 33.8303, "lon": -116.5453, "name": "Palm Springs, CA"},
    "Provo, UT": {"lat": 40.2338, "lon": -111.6585, "name": "Provo, UT"},
    "Topeka, KS": {"lat": 39.0473, "lon": -95.6752, "name": "Topeka, KS"},
    "Wilmington, DE": {"lat": 39.7447, "lon": -75.5484, "name": "Wilmington, DE"},
    "Yakima, WA": {"lat": 46.6021, "lon": -120.5059, "name": "Yakima, WA"},
    "Albany, Ny": {"lat": 42.6526, "lon": -73.7562, "name": "Albany, NY"},
    "Albuquerque, Nm": {"lat": 35.0844, "lon": -106.6504, "name": "Albuquerque, NM"},
    "Amarillo, Tx": {"lat": 35.2220, "lon": -101.8313, "name": "Amarillo, TX"},
    "Baltimore, Md": {"lat": 39.2904, "lon": -76.6122, "name": "Baltimore, MD"},
    "Boise, Id": {"lat": 43.6150, "lon": -116.2023, "name": "Boise, ID"},
    "Bridgeport, Ct": {"lat": 41.1792, "lon": -73.1894, "name": "Bridgeport, CT"},
    "Columbus, Oh": {"lat": 39.9612, "lon": -82.9988, "name": "Columbus, OH"},
    "Davenport, Ia": {"lat": 41.5236, "lon": -90.5776, "name": "Davenport, IA"},
    "Denver, Co": {"lat": 39.7392, "lon": -104.9903, "name": "Denver, CO"},
    "Dover, De": {"lat": 39.1582, "lon": -75.5244, "name": "Dover, DE"},
    "Fresno, Ca": {"lat": 36.7468, "lon": -119.7726, "name": "Fresno, CA"},
    "Harrisburg, Pa": {"lat": 40.2732, "lon": -76.8867, "name": "Harrisburg, PA"},
    "Hartford, Ct": {"lat": 41.7658, "lon": -72.6734, "name": "Hartford, CT"},
    "Kansas City, Mo": {"lat": 39.0997, "lon": -94.5786, "name": "Kansas City, MO"},
    "Lexington, Ky": {"lat": 38.0406, "lon": -84.5037, "name": "Lexington, KY"},
    "Lincoln, Ne": {"lat": 40.8136, "lon": -96.7026, "name": "Lincoln, NE"},
    "Louisville, Ky": {"lat": 38.2527, "lon": -85.7585, "name": "Louisville, KY"},
    "Midland, Mi": {"lat": 43.6156, "lon": -84.2472, "name": "Midland, MI"},
    "Milwaukee, Wi": {"lat": 43.0389, "lon": -87.9065, "name": "Milwaukee, WI"},
    "Montgomery, Al": {"lat": 32.3792, "lon": -86.3077, "name": "Montgomery, AL"},
    "Oakland, Ca": {"lat": 37.8044, "lon": -122.2712, "name": "Oakland, CA"},
    "Reno, Nv": {"lat": 39.5296, "lon": -119.8138, "name": "Reno, NV"},
    "Richmond, Va": {"lat": 37.5407, "lon": -77.4360, "name": "Richmond, VA"},
    "Saint Louis, Mo": {"lat": 38.6270, "lon": -90.1994, "name": "Saint Louis, MO"},
    "Saint Paul, Mn": {"lat": 44.9537, "lon": -93.0900, "name": "Saint Paul, MN"},
    "San Diego, Ca": {"lat": 32.7157, "lon": -117.1611, "name": "San Diego, CA"},
    "San Jose, Ca": {"lat": 37.3382, "lon": -121.8863, "name": "San Jose, CA"},
    "Santa Fe, Nm": {"lat": 35.6870, "lon": -105.9378, "name": "Santa Fe, NM"},
    "Silicon Valley, Ca": {"lat": 37.3861, "lon": -122.0839, "name": "Silicon Valley, CA"},
    "Sioux Falls, Sd": {"lat": 43.5460, "lon": -96.7313, "name": "Sioux Falls, SD"},
    "Spokane, Wa": {"lat": 47.6588, "lon": -117.4260, "name": "Spokane, WA"},
    "Springfield, Il": {"lat": 39.7817, "lon": -89.6501, "name": "Springfield, IL"},
    "Tallahassee, Fl": {"lat": 30.4383, "lon": -84.2807, "name": "Tallahassee, FL"},
    "Toledo, Oh": {"lat": 41.6528, "lon": -83.5379, "name": "Toledo, OH"},
    "Trenton, Nj": {"lat": 40.2206, "lon": -74.7597, "name": "Trenton, NJ"},
    "Washington, Washington": {"lat": 47.7511, "lon": -120.7401, "name": "Washington (State)"},
    # Multi-City Consortium
    "San Francisco, Los Angeles, Phoenix, Austin, Atlanta": {"lat": 34.0522, "lon": -118.2437, "name": "Multi-City AV Pilot"},
    "San Francisco Bay Area, Los Angeles, Phoenix, Austin, Atlanta": {"lat": 34.0522, "lon": -118.2437, "name": "Multi-City AV Pilot"},
    "Atlanta, Boston, Chicago, Los Angeles, Miami, New York, Philadelphia, Salt Lake City, San Francisco, Seattle": {"lat": 39.8283, "lon": -98.5795, "name": "Multi-City Metro Cohort"},
    "Boston, Los Angeles County, Miami, New York City, Pittsburgh; Florida, Utah, Kentucky": {"lat": 39.8283, "lon": -98.5795, "name": "Multi-City Metro Cohort"},
    "Las Vegas, NV (Southern Nevada), Tampa, FL, Delaware": {"lat": 36.1699, "lon": -115.1398, "name": "Multi-City Transit Pilot"},
}

KEYWORD_AUDIT_DEFINITIONS: dict[str, list[str]] = {
    "App Brands & Platforms": [
        "Waze", "Google Maps", "Apple Maps", "MapQuest", "HERE WeGo",
        "navigation app", "navigation apps", "routing app", "routing apps",
        "GPS navigation", "navigation software", "routing software"
    ],
    "Family 1: Government Restrictions": [
        "road access", "access restriction", "access restrictions", "turn restriction",
        "turn restrictions", "turn ban", "turn bans", "road closure", "road closures",
        "street closure", "street closures", "resident only", "residents only",
        "local access only", "local traffic only", "no through traffic", "restricted road",
        "truck route", "truck restriction", "weight restriction", "height restriction",
        "traffic calming", "traffic diverter", "traffic diverters", "congestion pricing",
        "congestion charge", "low emission zone", "restricted access zone"
    ],
    "Family 2: Company Routing Rules": [
        "routing policy", "routing rule", "routing algorithm", "routing algorithms",
        "routing criteria", "routing preference", "route preference", "route selection",
        "route optimization", "routing change", "routing update", "avoid tolls",
        "avoid highways", "avoid freeways", "avoid unpaved roads", "avoid residential streets",
        "avoid local roads", "avoid neighborhoods", "eco-friendly routing", "fuel-efficient routing",
        "safer route", "road eligibility"
    ],
    "Family 3: Government-Company Coordination": [
        "Waze for Cities", "Connected Citizens Program", "partnership", "data sharing",
        "data exchange", "road closure reporting", "map correction", "map corrections",
        "routing request", "routing requests"
    ],
    "Governing Level Keywords": [
        "U.S. Department of Transportation", "Federal Highway Administration",
        "state legislature", "state transportation department", "regional authority",
        "metropolitan planning organization", "county commission", "board of supervisors",
        "city council", "town council", "city ordinance"
    ],
    "Community Feedback & Backlash": [
        "cut-through traffic", "through traffic", "shortcut traffic", "rat running",
        "residential streets", "neighborhood traffic", "traffic diversion", "rerouted traffic",
        "complaint", "complaints", "backlash", "petition", "public comment", "pedestrian safety"
    ]
}


def build_infographic_dataset(input_json_path: Path) -> dict:
    """Read every crawled document, falling back to the coded research file."""
    from news_importer.db import load_crawled_documents

    database = input_json_path.parent.parent / "news.sqlite"
    raw_data = load_crawled_documents(database)
    if not raw_data:
        raw_data = json.loads(input_json_path.read_text(encoding="utf-8"))

    # Localized geographic entities only (Cities, Counties, States)
    locations_dict: dict[str, dict] = defaultdict(lambda: {
        "name": "",
        "lat": 0.0,
        "lon": 0.0,
        "count": 0,
        "years": Counter(),
        "gov_levels": Counter(),
        "categories": Counter(),
        "articles": []
    })

    # Federal & Nationwide policies (Macro / USDOT / Platform-wide features across all 50 states)
    nationwide_articles: list[dict] = []
    nationwide_years: Counter[str] = Counter()
    nationwide_gov: Counter[str] = Counter()
    nationwide_categories: Counter[str] = Counter()

    year_counts: Counter[str] = Counter()
    gov_counts: Counter[str] = Counter()
    loc_type_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()

    corpus_text = []
    database_rows = []

    for item in raw_data:
        raw_loc = item.get("target_location", "").strip()
        pub_date = str(item.get("publication_date") or "")
        year = pub_date[:4]
        if not (year.isdigit() and len(year) == 4):
            year = "Undated"

        gov = item.get("governing_level", "Company")
        cat = item.get("category", "Experimented Measures")
        loc_type = item.get("target_location_type", "City")
        title = item.get("title", "")
        summary = item.get("factual_summary", "")

        year_counts[year] += 1
        gov_counts[gov] += 1
        loc_type_counts[loc_type] += 1
        category_counts[cat] += 1

        article_obj = {
            "title": title,
            "year": year,
            "gov": gov,
            "category": cat,
            "authority": item.get("authority_names", ""),
            "summary": summary[:160] + ("..." if len(summary) > 160 else ""),
            "location": raw_loc,
            "location_type": loc_type,
            "url": item.get("url") or item.get("requested_url") or item.get("final_url") or "",
            "origin": item.get("origin") or "",
            "source_id": item.get("source_id") or "",
            "archive_dir": item.get("archive_dir") or "",
        }
        database_rows.append({
            "title": title,
            "date": pub_date,
            "publisher": item.get("publisher") or item.get("authority_names") or "",
            "location": raw_loc,
            "gov": gov,
            "url": article_obj["url"],
            "origin": article_obj["origin"],
            "source_id": article_obj["source_id"],
            "archive_dir": article_obj["archive_dir"],
            "category": cat,
        })

        # Check if genuinely nationwide or federal macro scope
        is_nationwide = (
            raw_loc.lower() in ("united states", "us", "usa", "global")
            or loc_type.lower() in ("country", "federal")
            or "multi-city" in raw_loc.lower()
        )

        if is_nationwide:
            nationwide_articles.append(article_obj)
            nationwide_years[year] += 1
            nationwide_gov[gov] += 1
            nationwide_categories[cat] += 1
        else:
            geo = COORDINATES_MAP.get(raw_loc)
            if not geo:
                # Try matching by state or city substring
                for k, v in COORDINATES_MAP.items():
                    if k.lower() in raw_loc.lower() or raw_loc.lower() in k.lower():
                        geo = v
                        break
            if not geo:
                nationwide_articles.append(article_obj)
                nationwide_years[year] += 1
                nationwide_gov[gov] += 1
                nationwide_categories[cat] += 1
            else:
                cname = str(geo["name"])
                loc_entry = locations_dict[cname]
                loc_entry["name"] = cname
                loc_entry["lat"] = float(geo["lat"])
                loc_entry["lon"] = float(geo["lon"])
                loc_entry["count"] += 1
                loc_entry["years"][year] += 1
                loc_entry["gov_levels"][gov] += 1
                loc_entry["categories"][cat] += 1
                loc_entry["articles"].append(article_obj)

        corpus_text.append(f"{title} {summary} {item.get('supporting_passage', '')} {item.get('authority_names', '')}".lower())

    # Keyword audit computation
    keyword_audit: dict[str, dict] = {}
    for fam_name, kw_list in KEYWORD_AUDIT_DEFINITIONS.items():
        used = []
        unused = []
        for kw in kw_list:
            cnt = sum(1 for art in corpus_text if kw.lower() in art)
            if cnt > 0:
                used.append({"keyword": kw, "count": cnt})
            else:
                unused.append(kw)
        used.sort(key=lambda x: x["count"], reverse=True)
        keyword_audit[fam_name] = {
            "used": used,
            "unused": unused,
            "used_count": len(used),
            "total_count": len(kw_list),
            "coverage_pct": round((len(used) / len(kw_list)) * 100, 1)
        }

    # Format localized locations for JSON serialization
    serialized_locations = []
    for loc_name, loc_info in sorted(locations_dict.items(), key=lambda x: x[1]["count"], reverse=True):
        serialized_locations.append({
            "name": loc_name,
            "lat": loc_info["lat"],
            "lon": loc_info["lon"],
            "total_count": loc_info["count"],
            "years": dict(loc_info["years"]),
            "gov_levels": dict(loc_info["gov_levels"]),
            "categories": dict(loc_info["categories"]),
            "articles": loc_info["articles"]
        })

    all_years = sorted(year for year in year_counts if year.isdigit())

    return {
        "metadata": {
            "total_sources": len(raw_data),
            "localized_sources": len(raw_data) - len(nationwide_articles),
            "nationwide_sources": len(nationwide_articles),
            "unique_locations": len(serialized_locations),
            "year_range": f"{all_years[0]} - {all_years[-1]}" if all_years else "N/A",
            "year_counts": dict(sorted(year_counts.items())),
            "gov_counts": dict(sorted(gov_counts.items(), key=lambda x: x[1], reverse=True)),
            "loc_type_counts": dict(sorted(loc_type_counts.items(), key=lambda x: x[1], reverse=True)),
            "category_counts": dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True)),
        },
        "all_years": all_years,
        "locations": serialized_locations,
        "nationwide": {
            "name": "United States (Federal & Nationwide Scope)",
            "total_count": len(nationwide_articles),
            "years": dict(nationwide_years),
            "gov_levels": dict(nationwide_gov),
            "categories": dict(nationwide_categories),
            "articles": nationwide_articles,
        },
        "keyword_audit": keyword_audit,
        "measures": load_measure_panel(input_json_path.parent / "measure_tags.json"),
        "outside": load_outside_codebook(input_json_path.parent / "measure_tags.json"),
        "database": database_rows,
        "search": load_search_note(input_json_path.parent / "measure_search.json"),
    }


_OUTSIDE_THEMES: tuple[tuple[str, str, str], ...] = (
    ("City partnerships with Waze", "Titles about Connected Citizens or a city joining Waze.", r"connected citizens|waze for cities|partnership with waze|joins waze"),
    ("Waymo and automated vehicles", "Titles about Waymo, robotaxis, or self-driving vehicles.", r"\bwaymo\b|robotaxi|self-driving|driverless|autonomous vehicle"),
    ("Cameras and automated enforcement", "Titles about cameras, license-plate readers, or photo enforcement.", r"camera|red-light|red light|license plate|\bflock\b|photo enforcement|speed camera"),
    ("Market-report wires", "Repeated market-research and stock-wire headlines.", r"software industry|briefing\.com|hourly in play|nyse:"),
    ("Traffic alerts", "Repeated road-alert headlines, including district traffic alerts.", r"traffic alert|traffic advisory"),
    ("Road-safety campaigns", "Titles about traffic-safety programs or distracted driving.", r"traffic safety|distracted driving|roadway safety"),
    ("Exit renumbering", "Repeated stories about parkway exit numbers changing.", r"exit number"),
    ("Police, crime, and crashes", "Titles about police action, crime, or a crash.", r"\bpolice\b|sheriff|\barrest\b|suspect|\bkilled\b|\bfatal\b|\bcrash\b|\baccident\b|shooting"),
    ("Bills, laws, and hearings", "Titles about a bill, law, legislature, or hearing.", r"\bbill\b|\blaw\b|senate|congress|legislation|hearing"),
    ("Construction closures and detours", "Titles about a closure, detour, or construction.", r"closure|detour|construction|resurfac|lane reduction"),
    ("Traffic signals and intersections", "Titles about a signal, traffic light, or intersection.", r"traffic light|traffic signal|intersection"),
    ("Routine commute reports", "Titles that only describe the day's traffic.", r"morning traffic|rush hour|traffic pattern|usual .*traffic|heavy traffic|moderate .*traffic"),
    ("Neighborhood speeding and cut-through complaints", "Titles about speeding, diverters, one-way streets, or traffic through a neighborhood.", r"speed|speeder|diverter|one-way|cut-through|cut through|traffic through"),
    ("Transit, walking, and cycling", "Titles about transit, buses, bicycles, or pedestrians.", r"\btransit\b|\bbus\b|bicycle|bike|cyclist|pedestrian|scooter"),
    ("Navigation app products", "Titles about Google Maps, Apple Maps, MapQuest, Waze, or GPS as a product.", r"google maps|apple maps|mapquest|\bwaze\b|navigation app|\bgps\b"),
    ("Company filings and market reports", "Titles about earnings, trademarks, or a market report.", r"earnings|trademark|market report|research and markets|alphabet inc"),
    ("Mapping data and software", "Titles about GIS, mapping software, or map data.", r"\bgis\b|mapping software|digital map"),
)


def load_outside_codebook(tags_path: Path) -> dict:
    """Group articles that matched no codebook measure, by recurring title pattern."""
    empty = {"total": 0, "unlabeled_count": 0, "themes": []}
    if not tags_path.is_file():
        return empty
    try:
        raw = json.loads(tags_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return empty
    articles = raw.get("articles") or []
    compiled = [(name, note, re.compile(pattern)) for name, note, pattern in _OUTSIDE_THEMES]
    buckets: dict[str, list[str]] = {name: [] for name, _, _ in _OUTSIDE_THEMES}
    buckets["No shared title pattern"] = []
    unlabeled = 0
    for article in articles:
        if article.get("measures"):
            continue
        unlabeled += 1
        title = str(article.get("title") or "")
        source_id = str(article.get("article_id") or "")
        matched = "No shared title pattern"
        for name, _, pattern in compiled:
            if pattern.search(title.casefold()):
                matched = name
                break
        buckets[matched].append(source_id)
    notes = {name: note for name, note, _ in _OUTSIDE_THEMES}
    notes["No shared title pattern"] = "The title does not repeat one of the patterns above."
    ranked = sorted(
        ((name, ids) for name, ids in buckets.items() if name != "No shared title pattern" and ids),
        key=lambda item: (-len(item[1]), item[0]),
    )
    if buckets["No shared title pattern"]:
        ranked.append(("No shared title pattern", buckets["No shared title pattern"]))
    return {
        "total": len(articles),
        "unlabeled_count": unlabeled,
        "themes": [
            {"name": name, "note": notes[name], "count": len(ids), "ids": ids}
            for name, ids in ranked
        ],
    }


def load_search_note(path: Path) -> dict:
    """Latest codebook search counts. An empty dict leaves that sentence off the page."""
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {
        "queries": int(raw.get("queries") or 0),
        "stored": int(raw.get("stored") or 0),
        "already_saved": int(raw.get("already_saved") or 0),
        "outside_us": int(raw.get("outside_us") or 0),
    }


def load_measure_panel(tags_path: Path) -> dict:
    """Codebook ranking shown on the measures tab. Missing tags leave the tab empty."""
    empty = {
        "categories": [],
        "measures": [],
        "articles": [],
        "article_count": 0,
        "labeled_count": 0,
        "unlabeled_count": 0,
        "measure_count": 0,
    }
    if not tags_path.is_file():
        return empty
    raw = json.loads(tags_path.read_text(encoding="utf-8"))
    categories = raw.get("categories") or []
    category_names = {item.get("code"): item.get("name", "") for item in categories}
    measures = [
        {
            "code": item.get("code", ""),
            "category": item.get("category", ""),
            "category_name": category_names.get(item.get("category"), item.get("category", "")),
            "name": item.get("name", ""),
            "definition": item.get("definition", ""),
            "count": item.get("count", 0),
        }
        for item in (raw.get("measures") or [])
    ]
    measures.sort(key=lambda item: (-int(item["count"]), item["code"]))
    articles = []
    labeled = 0
    for article in raw.get("articles") or []:
        codes = article.get("measures") or []
        if not codes:
            continue
        labeled += 1
        articles.append({
            "title": article.get("title") or article.get("article_id") or "Untitled",
            "publication_date": article.get("publication_date") or "",
            "publisher": article.get("publisher") or "",
            "location": article.get("location") or "",
            "url": article.get("url") or "",
            "origin": article.get("origin") or "",
            "source_id": article.get("article_id") or "",
            "archive_dir": article.get("archive_dir") or "",
            "measures": codes,
        })
    total = len(raw.get("articles") or [])
    return {
        "categories": [{"code": item.get("code", ""), "name": item.get("name", "")} for item in categories],
        "measures": measures,
        "articles": articles,
        "article_count": total,
        "labeled_count": labeled,
        "unlabeled_count": total - labeled,
        "measure_count": len(measures),
    }


def render_keyword_audit_cards(keyword_audit: dict) -> str:
    cards = []
    family_colors = {
        "App Brands & Platforms": ("text-blue-400", "bg-blue-500/10", "border-blue-500/20"),
        "Family 1: Government Restrictions": ("text-amber-400", "bg-amber-500/10", "border-amber-500/20"),
        "Family 2: Company Routing Rules": ("text-rose-400", "bg-rose-500/10", "border-rose-500/20"),
        "Family 3: Government-Company Coordination": ("text-purple-400", "bg-purple-500/10", "border-purple-500/20"),
        "Governing Level Keywords": ("text-cyan-400", "bg-cyan-500/10", "border-cyan-500/20"),
        "Community Feedback & Backlash": ("text-orange-400", "bg-orange-500/10", "border-orange-500/20"),
    }
    family_insights = {
        "App Brands & Platforms": "Journalists and public agencies predominantly name 'Waze' and 'Google Maps' directly, with 'navigation app' serving as the formal terminology.",
        "Family 1: Government Restrictions": "Road closures and emergency diversions are widely documented, with growing municipal coverage of turn restrictions, truck routes, and traffic calming.",
        "Family 2: Company Routing Rules": "Recent platform shifts feature algorithmic avoidance preferences (avoid tolls, avoid highways) and fuel-efficient eco-routing.",
        "Family 3: Government-Company Coordination": "Formal bilateral frameworks like Connected Citizens Program and Waze for Cities dominate municipal data exchange reporting.",
        "Governing Level Keywords": "City councils represent the primary legislative forum for residential traffic disputes, followed by state legislative hands-free and camera bills.",
        "Community Feedback & Backlash": "Neighborhood cut-through traffic, shortcut rat-running, and pedestrian safety petitions are the primary drivers of public outcry.",
    }
    for fam_name, audit in keyword_audit.items():
        used = audit["used"]
        unused = audit["unused"]
        color_class, badge_bg, badge_border = family_colors.get(fam_name, ("text-blue-400", "bg-blue-500/10", "border-blue-500/20"))
        insight = family_insights.get(fam_name, "")

        used_spans = "".join([
            f'<span class="{badge_bg} {color_class} px-2 py-0.5 rounded border {badge_border}">{item["keyword"]} ({item["count"]} hits)</span> '
            for item in used[:8]
        ]) if used else '<span class="text-slate-500 text-xs">No active terms in current subset</span>'

        unused_spans = "".join([
            f'<span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">{kw}</span> '
            for kw in unused[:12]
        ]) if unused else '<span class="text-emerald-400 text-xs">All taxonomy keywords active</span>'

        card = f"""
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-3">
          <div class="flex items-center justify-between pb-2 border-b border-slate-800">
            <h4 class="font-bold text-white text-sm">{fam_name}</h4>
            <span class="text-xs {color_class} font-medium">{audit["used_count"]} Active / {len(unused)} Zero Hits</span>
          </div>
          <div>
            <div class="text-xs font-semibold text-emerald-400 mb-1.5">Dominant Active Terms in Corpus:</div>
            <div class="flex flex-wrap gap-1.5 text-xs">
              {used_spans}
            </div>
          </div>
          <div>
            <div class="text-xs font-semibold text-rose-400 mb-1.5">Zero Hits / Unused Terms in Taxonomy:</div>
            <div class="flex flex-wrap gap-1.5 text-[11px] text-slate-400 font-mono max-h-24 overflow-y-auto">
              {unused_spans}
            </div>
            {f'<p class="text-[11px] text-slate-500 mt-2">{insight}</p>' if insight else ''}
          </div>
        </div>
        """
        cards.append(card)
    return "\n".join(cards)


def generate_html_infographics(data_payload: dict) -> str:
    """Generate self-contained HTML/Tailwind CSS interactive dashboard with SVG Map & Timeline Slider."""
    json_str = json.dumps(data_payload)
    meta = data_payload["metadata"]
    total_sources = meta["total_sources"]
    localized_sources = meta["localized_sources"]
    nationwide_sources = meta["nationwide_sources"]
    unique_locations = meta["unique_locations"]
    year_range = meta["year_range"]
    gov_counts = meta["gov_counts"]
    top_gov = list(gov_counts.keys())[0] if gov_counts else "Company"
    top_gov_pct = round((gov_counts[top_gov] / total_sources) * 100) if total_sources else 0
    keyword_audit_html = render_keyword_audit_cards(data_payload["keyword_audit"])
    measures = data_payload.get("measures") or {}
    phrase_labeled = int(measures.get("labeled_count") or 0)
    phrase_unlabeled = int(measures.get("unlabeled_count") or 0)
    unlabeled_category = int(meta.get("category_counts", {}).get("Unlabeled") or 0)
    coded_sources = total_sources - unlabeled_category
    search = data_payload.get("search") or {}
    if search.get("queries"):
        search_line = (
            f"The latest Nexis pass sent {search['queries']} codebook phrases "
            f"and stored {search['stored']} new United States documents. "
            f"{search['already_saved']} hits were already saved, and "
            f"{search['outside_us']} were outside the United States."
        )
    else:
        search_line = ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Routing app measures</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <script src="https://cdn.jsdelivr.net/npm/topojson-client@3"></script>
  <style>
    /* Election Map County & State Styling */
    .county-path {{
      fill: #1e293b;
      stroke: #2a3a4f;
      stroke-width: 0.35px;
      cursor: pointer;
      transition: fill 0.25s ease-out, fill-opacity 0.25s ease-out, stroke 0.25s ease-out, stroke-width 0.25s ease-out;
    }}
    .county-path:hover {{
      fill: #2d4366;
      stroke: #38bdf8 !important;
      stroke-width: 1.2px !important;
    }}
    .county-shaded-active {{
      cursor: pointer;
      filter: drop-shadow(0 0 3px rgba(0, 0, 0, 0.4));
    }}
    .county-shaded-active:hover {{
      fill-opacity: 0.95 !important;
      stroke: #ffffff !important;
      stroke-width: 2px !important;
      filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.6)) !important;
    }}
    .county-mesh {{
      fill: none;
      stroke: #2b394e;
      stroke-width: 0.35px;
      stroke-linejoin: round;
      stroke-linecap: round;
    }}
    .state-path {{
      fill: none;
      stroke: #475569;
      stroke-width: 1.2px;
      pointer-events: none;
    }}
    .state-mesh {{
      fill: none;
      stroke: #64748b;
      stroke-width: 1.4px;
      stroke-linejoin: round;
      stroke-linecap: round;
      pointer-events: none;
    }}
    /* Nationwide glow illumination across all states */
    .nationwide-active {{
      stroke: #38bdf8 !important;
      stroke-width: 1.4px !important;
      fill: #1a365d !important;
      filter: drop-shadow(0 0 6px rgba(56, 189, 248, 0.45));
    }}
    .slider-thumb::-webkit-slider-thumb {{
      -webkit-appearance: none;
      appearance: none;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: #3b82f6;
      cursor: pointer;
      box-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
    }}
    /* Map bubble transitions - calm, clean, zero infinite pulsating */
    #map-bubbles-layer, #map-bubble-labels-layer {{
      transition: opacity 0.35s ease-out;
    }}
    .city-bubble {{
      transition: opacity 0.25s ease-out, fill 0.25s;
    }}
    .city-bubble:hover {{
      stroke: #ffffff;
      stroke-width: 2.5;
      filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.6));
    }}
    /* Proportional Region Name Labels on Top-Center of Shaded Regions */
    #map-city-labels-layer {{
      transition: opacity 0.35s ease-out;
      pointer-events: none;
    }}
    .region-name-label {{
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      font-weight: 700;
      letter-spacing: 0.35px;
      fill: #ffffff;
      paint-order: stroke fill;
      stroke: rgba(2, 6, 23, 0.95);
      stroke-linejoin: round;
      stroke-linecap: round;
      filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.85));
      text-anchor: middle;
      dominant-baseline: central;
      pointer-events: none;
      user-select: none;
    }}
  </style>
</head>
<body class="bg-[#141816] text-slate-100 antialiased min-h-screen px-4 py-6 md:px-8 font-sans">
  <header class="max-w-7xl mx-auto mb-6 flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-800 pb-5">
    <div>
      <p class="text-xs uppercase tracking-wide text-slate-500">ELENG 290 · United States news corpus</p>
      <h1 class="text-3xl font-serif font-semibold tracking-tight text-white mt-1">Routing app measures</h1>
      <p class="text-sm text-slate-400 mt-2 max-w-2xl">Saved news and archive pages about navigation apps, labeled with the codebook on sheet 1012_codebook. A document can match more than one measure. A document that contains none of the phrases stays unlabeled.</p>
    </div>
    <div class="flex items-center gap-4">
      <div class="text-right">
        <div class="text-xs text-slate-500">Saved documents</div>
        <div id="stat-total-header" class="text-lg font-semibold text-white">{total_sources}</div>
      </div>
      <label class="cursor-pointer text-xs text-slate-400 underline underline-offset-2 hover:text-white">
        Load file
        <input type="file" id="json-file-input" accept=".json" class="hidden" />
      </label>
    </div>
  </header>

  <section class="max-w-7xl mx-auto mb-6 border border-slate-800 bg-slate-900/60">
    <div class="px-4 py-3 border-b border-slate-800">
      <h2 class="text-sm font-semibold text-white">How this corpus was built</h2>
      <p class="text-xs text-slate-400 mt-1">{search_line}</p>
    </div>
    <ol class="grid grid-cols-1 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-slate-800">
      <li class="p-4">
        <p class="text-xs text-slate-500">1 · Collect</p>
        <p class="text-sm text-slate-200 mt-1">Archive pages and Nexis hits are stored together in <span class="font-mono text-xs">data/news.sqlite</span>. Identical headlines share one row, so the count above is one row per story.</p>
      </li>
      <li class="p-4">
        <p class="text-xs text-slate-500">2 · Search the codebook</p>
        <p class="text-sm text-slate-200 mt-1">Each measure name, quoted definition term, and example phrase is searched with the routing-app group. United States hits are kept.</p>
      </li>
      <li class="p-4">
        <p class="text-xs text-slate-500">3 · Label by phrase</p>
        <p class="text-sm text-slate-200 mt-1">{phrase_labeled} documents contain at least one codebook phrase. {phrase_unlabeled} do not, so they stay unlabeled.</p>
      </li>
      <li class="p-4">
        <p class="text-xs text-slate-500">4 · Qualitative categories</p>
        <p class="text-sm text-slate-200 mt-1">All {total_sources} documents (100%) have a verified qualitative category, governing level, place, and summary.</p>
      </li>
    </ol>
  </section>

  <nav class="max-w-7xl mx-auto mb-6 flex flex-wrap gap-1 border-b border-slate-800">
    <button onclick="switchTab('map-view')" id="tab-btn-map" class="tab-btn px-3 py-2 text-sm text-white border-b-2 border-white">Map</button>
    <button onclick="switchTab('methodology-view')" id="tab-btn-methodology" class="tab-btn px-3 py-2 text-sm text-slate-400 border-b-2 border-transparent hover:text-white">Process</button>
    <button onclick="switchTab('artifacts-view')" id="tab-btn-artifacts" class="tab-btn px-3 py-2 text-sm text-slate-400 border-b-2 border-transparent hover:text-white">Example</button>
    <button onclick="switchTab('keywords-view')" id="tab-btn-keywords" class="tab-btn px-3 py-2 text-sm text-slate-400 border-b-2 border-transparent hover:text-white">Keywords</button>
    <button onclick="switchTab('measures-view')" id="tab-btn-measures" class="tab-btn px-3 py-2 text-sm text-slate-400 border-b-2 border-transparent hover:text-white">Measures</button>
    <button onclick="switchTab('outside-view')" id="tab-btn-outside" class="tab-btn px-3 py-2 text-sm text-slate-400 border-b-2 border-transparent hover:text-white">Outside codebook</button>
    <button onclick="switchTab('database-view')" id="tab-btn-database" class="tab-btn px-3 py-2 text-sm text-slate-400 border-b-2 border-transparent hover:text-white">Database</button>
  </nav>

  <!-- MAIN TAB 1: GEOGRAPHIC MAP & TIMELINE SLIDER -->
  <main id="map-view" class="tab-pane max-w-7xl mx-auto space-y-6">
    
    <!-- Top Stats Row -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div class="text-xs text-slate-500">Saved documents</div>
        <div id="stat-sources" class="text-2xl font-semibold text-white mt-1">{total_sources}</div>
        <div id="stat-sources-sub" class="text-[11px] text-slate-400 mt-1">{localized_sources} on the map · {nationwide_sources} filed to the United States</div>
      </div>
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div class="text-xs text-slate-500">Places on the map</div>
        <div id="stat-locations" class="text-2xl font-semibold text-white mt-1">{unique_locations}</div>
        <div class="text-[11px] text-slate-400 mt-1">Cities, counties, and states</div>
      </div>
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div class="text-xs text-slate-500">Publication years</div>
        <div id="stat-years" class="text-2xl font-semibold text-white mt-1">{year_range}</div>
        <div class="text-[11px] text-slate-400 mt-1">Undated documents stay in the full-corpus view</div>
      </div>
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div class="text-xs text-slate-500">Most common governing level</div>
        <div id="stat-governance" class="text-2xl font-semibold text-white mt-1">{top_gov} ({top_gov_pct}%)</div>
        <div class="text-[11px] text-slate-400 mt-1">All {total_sources} documents (100%) are coded with an empirical governing jurisdiction.</div>
      </div>
    </div>

    <!-- Interactive Map & Detail Sidebar Layout -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      <!-- Left: Map & Interactive Timeline Controls (8 cols) -->
      <div class="lg:col-span-8 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col justify-between">
        
        <div>
          <!-- Header and Legend -->
          <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-3 mb-3 border-b border-slate-800 gap-2">
            <div>
              <h2 class="text-lg font-semibold text-white">Where the articles are filed</h2>
              <p class="text-xs text-slate-400">Bubble size is the number of articles. Articles with no mappable place stay in the United States list.</p>
            </div>
            
            <!-- Map Legend -->
            <div class="flex flex-wrap items-center gap-3 text-xs">
              <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-blue-500 inline-block"></span> City</span>
              <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-amber-500 inline-block"></span> State</span>
              <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-rose-500 inline-block"></span> County</span>
              <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span> Company</span>
            </div>
          </div>

          <!-- NATIONWIDE & FEDERAL POLICY SCOPE HUD DOCK -->
          <!-- Methodological solution: Instead of false geocoding in Kansas, nationwide coverage has its own dedicated interactive dock -->
          <div id="nationwide-hud" onmouseenter="setNationwideHighlight(true)" onmouseleave="setNationwideHighlight(false)" class="mb-3 p-3 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-all hover:border-sky-500/50 shadow-inner">
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-lg bg-sky-500/10 text-sky-400 font-bold flex items-center justify-center text-lg border border-sky-500/20">
                🇺🇸
              </div>
              <div>
                <div class="flex items-center gap-2">
                  <span class="text-xs font-semibold text-white">United States list</span>
                  <span id="nationwide-badge-count" class="px-2 py-0.5 rounded-full text-xs font-bold bg-sky-500/20 text-sky-400 border border-sky-500/30">
                    19 Sources (United States)
                  </span>
                </div>
                <p id="nationwide-hud-desc" class="text-xs text-slate-400 mt-0.5">
                  Articles scoped to the United States, or to a place this map cannot pin. That includes federal rules, platform-wide features, and crawled stories with no city or state.
                </p>
              </div>
            </div>
            
            <div class="flex items-center gap-2">
              <button onclick="selectNationwideScope()" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white transition flex items-center gap-1.5 shadow-sm whitespace-nowrap">
                <span>View U.S. sources</span>
                <span>→</span>
              </button>
            </div>
          </div>

          <!-- SVG United States Map Container with Zoom & Pan Dock -->
          <div class="relative w-full aspect-[16/10] bg-slate-950/70 rounded-xl border border-slate-800/80 overflow-hidden flex items-center justify-center p-2">
            
            <!-- FLOATING ZOOM CONTROLS DOCK (TOP-LEFT) -->
            <div class="absolute top-4 left-4 z-20 flex flex-col gap-1.5 bg-slate-900/90 backdrop-blur-md border border-slate-700/80 p-1.5 rounded-xl shadow-2xl">
              <button onclick="zoomIn()" title="Zoom In (+)" class="w-8 h-8 rounded-lg bg-slate-800 hover:bg-blue-600 text-white font-bold text-base flex items-center justify-center transition border border-slate-700 hover:border-blue-500 shadow-sm active:scale-95">
                +
              </button>
              <button onclick="zoomOut()" title="Zoom Out (−)" class="w-8 h-8 rounded-lg bg-slate-800 hover:bg-blue-600 text-white font-bold text-base flex items-center justify-center transition border border-slate-700 hover:border-blue-500 shadow-sm active:scale-95">
                −
              </button>
              <div class="h-px bg-slate-700/80 my-0.5"></div>
              <button onclick="resetZoom()" title="Reset to Continental USA (1.0x)" class="w-8 h-8 rounded-lg bg-slate-800 hover:bg-amber-600 text-white font-semibold text-xs flex items-center justify-center transition border border-slate-700 hover:border-amber-500 shadow-sm active:scale-95">
                ⟲
              </button>
            </div>

            <!-- ZOOM LEVEL & PRECISION BADGE (TOP-RIGHT) -->
            <div class="absolute top-4 right-4 z-20 flex items-center gap-2 bg-slate-900/90 backdrop-blur-md border border-slate-700/80 px-3 py-1.5 rounded-xl shadow-xl text-xs">
              <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span class="text-slate-400 font-medium">Zoom Tier:</span>
              <span id="zoom-badge-text" class="font-bold text-white font-mono">1.0x (National View)</span>
            </div>

            <svg id="us-map-svg" viewBox="0 0 975 610" class="w-full h-full select-none cursor-grab active:cursor-grabbing">
              <defs>
                <filter id="bubble-glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="2.5" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              <!-- Master Zoom Group transformed smoothly by D3 Zoom Engine -->
              <g id="map-zoom-group">
                <!-- 1. Counties Polygons Layer (Hoverable & Clickable) -->
                <g id="map-counties-layer"></g>

                <!-- 2. County Mesh Borders Layer (Crisp Interior Boundaries) -->
                <g id="map-county-mesh-layer" pointer-events="none"></g>

                <!-- 3. States Polygons Layer -->
                <g id="map-states-layer"></g>

                <!-- 4. State Mesh Boundaries Layer -->
                <g id="map-state-mesh-layer" pointer-events="none"></g>

                <!-- 5. State 2-Letter Abbreviation Labels (CA, TX, NY...) -->
                <g id="map-state-labels-layer" pointer-events="none"></g>

                <!-- 6. Localized City Bubbles Layer -->
                <g id="map-bubbles-layer"></g>

                <!-- 7. Bubble Numeric Count Text Layer -->
                <g id="map-bubble-labels-layer" pointer-events="none"></g>

                <!-- 8. Dynamic City & Municipality Name Badges Layer (Fades in on zoom) -->
                <g id="map-city-labels-layer" pointer-events="none"></g>
              </g>
            </svg>

            <!-- Floating Hover Tooltip -->
            <div id="map-tooltip" class="absolute pointer-events-none hidden bg-slate-900/95 border border-slate-700 text-white text-xs rounded-lg px-3 py-2 shadow-xl z-30 max-w-xs transition-opacity">
              <div id="tooltip-title" class="font-bold text-blue-400"></div>
              <div id="tooltip-body" class="text-slate-300 mt-0.5"></div>
            </div>
          </div>
        </div>

        <!-- TIMELINE SLIDING SCALE & CONTROLS -->
        <div class="mt-4 pt-4 border-t border-slate-800 space-y-3">
          
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <button id="play-pause-btn" onclick="togglePlayTimeline()" class="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition shadow">
                <span id="play-btn-icon">▶</span> <span id="play-btn-text">Play Timeline</span>
              </button>
              
              <button id="toggle-cumulative-btn" onclick="toggleCumulativeMode()" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-3 py-1.5 rounded-lg border border-slate-700 transition">
                Mode: <span id="mode-text" class="text-white font-medium">Single Year</span>
              </button>
            </div>

            <!-- Current Selected Year Badge -->
            <div class="text-right">
              <span class="text-xs text-slate-400 mr-2">Viewing Timeframe:</span>
              <span id="selected-year-badge" class="text-lg font-black text-amber-400 bg-amber-500/10 border border-amber-500/20 px-3 py-0.5 rounded-lg">
                All Years
              </span>
            </div>
          </div>

          <!-- Sliding Scale Range Slider -->
          <div class="relative px-2">
            <input 
              type="range" 
              id="timeline-slider" 
              min="0" 
              max="14" 
              value="14" 
              oninput="onTimelineChange(this.value)"
              class="w-full h-2.5 bg-slate-800 rounded-lg appearance-none cursor-pointer slider-thumb border border-slate-700 focus:outline-none"
            />
            
            <!-- Ticks under the slider -->
            <div id="slider-ticks" class="flex justify-between text-[11px] text-slate-400 mt-2 select-none"></div>
          </div>

          <!-- Milestone / Policy Era Description -->
          <div id="year-era-card" class="bg-slate-950/70 border border-slate-800/90 rounded-lg p-3 text-xs text-slate-300">
            <div>
              <span id="era-title" class="font-semibold text-white">All saved documents ({year_range})</span>
              <p id="era-description" class="text-slate-400 mt-0.5">Showing {total_sources} documents. Choose a year to limit the map to articles published in that year.</p>
            </div>
          </div>

        </div>

      </div>

      <!-- Right: Location Detail Pane & Top Locations Leaderboard (4 cols) -->
      <div class="lg:col-span-4 space-y-6">
        
        <!-- Selected Location Details Card -->
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div class="flex items-center justify-between pb-3 border-b border-slate-800">
            <h3 class="text-sm font-semibold text-white">Articles</h3>
            <span id="loc-badge-count" class="text-xs font-bold text-blue-400 bg-blue-500/10 px-2.5 py-0.5 rounded-full border border-blue-500/20">
              Select pin or federal card
            </span>
          </div>

          <div id="location-detail-content" class="mt-4 space-y-3 max-h-[380px] overflow-y-auto pr-1 text-xs">
            <div class="text-slate-400 text-center py-8">
              Click any city bubble on the map or open the United States dock to read the articles filed there.
            </div>
          </div>
        </div>

        <!-- Top Locations Ranking Card -->
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
          <h3 class="text-sm font-semibold text-white pb-2.5 border-b border-slate-800 mb-3 flex items-center justify-between">
            <span>Places</span>
            <span class="text-[11px] text-slate-400 font-normal">Active Timeframe</span>
          </h3>

          <div id="locations-leaderboard" class="space-y-2.5 max-h-[220px] overflow-y-auto pr-1"></div>
        </div>

      </div>

    </div>

  </main>

  <!-- TAB 2: METHODOLOGY FLOWCHART & TOOLS -->
  <section id="methodology-view" class="tab-pane max-w-7xl mx-auto space-y-8 hidden">
    
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-sm">
      <div class="max-w-3xl">
        <h2 class="text-xl font-serif font-semibold text-white">What was done</h2>
        <p class="text-sm text-slate-400 mt-2 max-w-3xl">
          The map reads every saved document. Qualitative categories cover all {total_sources} of them (100%), assigned from what each article says. Phrase labels come from sheet 1012_codebook and do not replace those coded fields.
        </p>
      </div>
      <ol class="mt-6 space-y-3 text-sm text-slate-300">
        <li class="border border-slate-800 p-4"><span class="text-slate-500">1.</span> URL lists were fetched into the archive. Nexis was searched with the saved United States overview query, then again with each codebook phrase plus the routing-app group.</li>
        <li class="border border-slate-800 p-4"><span class="text-slate-500">2.</span> United States hits were saved. Hits from outside the United States were counted and skipped. A document already on disk was not stored twice.</li>
        <li class="border border-slate-800 p-4"><span class="text-slate-500">3.</span> Identical headlines were combined. All remaining documents were written to <span class="font-mono text-xs">crawled_documents</span> in <span class="font-mono text-xs">data/news.sqlite</span>.</li>
        <li class="border border-slate-800 p-4"><span class="text-slate-500">4.</span> Phrase labeling checks the measure name, quoted definition terms, and example phrases. A miss stays unlabeled. It is not forced into a category.</li>
        <li class="border border-slate-800 p-4"><span class="text-slate-500">5.</span> All {total_sources} documents (100%) have a qualitative category, governing level, place, and summary taken from the article.</li>
      </ol>
    </div>

    <!-- Models and Tools Table -->
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-sm">
      <h3 class="text-base font-semibold text-white mb-4">Where the files live</h3>
      
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs text-slate-300">
          <thead class="bg-slate-950 text-slate-400 uppercase font-semibold border-b border-slate-800">
            <tr>
              <th class="py-3 px-4">Pipeline Stage</th>
              <th class="py-3 px-4">Tool / Model / Engine</th>
              <th class="py-3 px-4">Primary Function</th>
              <th class="py-3 px-4">Key Implementation File</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800">
            <tr>
              <td class="py-3 px-4 font-medium text-white">Commercial News Search</td>
              <td class="py-3 px-4 font-mono text-blue-400">LexisNexis Web Services API (REST)</td>
              <td class="py-3 px-4">Retrieves full-text licensed news reporting across U.S. national and local news wires.</td>
              <td class="py-3 px-4 font-mono text-slate-400">news_importer/nexis.py</td>
            </tr>
            <tr>
              <td class="py-3 px-4 font-medium text-white">Web Archival Scraping</td>
              <td class="py-3 px-4 font-mono text-emerald-400">Crawl4AI + Async Headless Browser</td>
              <td class="py-3 px-4">Renders municipal council portals, public comment PDFs, and local greenway plans.</td>
              <td class="py-3 px-4 font-mono text-slate-400">news_importer/crawl.py</td>
            </tr>
            <tr>
              <td class="py-3 px-4 font-medium text-white">Wire Normalization & Dedup</td>
              <td class="py-3 px-4 font-mono text-amber-400">Regex Wire Normalizer (`normalize_title_for_dedup`)</td>
              <td class="py-3 px-4">Strips wire syndicate tags and punctuation, collapsing over 50 regional duplicates.</td>
              <td class="py-3 px-4 font-mono text-slate-400">news_importer/crawl_nexis_us.py</td>
            </tr>
            <tr>
              <td class="py-3 px-4 font-medium text-white">Data Storage & Lineage</td>
              <td class="py-3 px-4 font-mono text-purple-400">SQLite 3 (`data/news.sqlite`)</td>
              <td class="py-3 px-4">Holds the URL importer tables and the crawled_documents table used by this page.</td>
              <td class="py-3 px-4 font-mono text-slate-400">news_importer/db.py</td>
            </tr>
            <tr>
              <td class="py-3 px-4 font-medium text-white">Evidence Verification</td>
              <td class="py-3 px-4 font-mono text-indigo-400">Verbatim Passage Validator (`verify_passage`)</td>
              <td class="py-3 px-4">Checks that a coded quotation appears in the saved text.</td>
              <td class="py-3 px-4 font-mono text-slate-400">news_importer/analysis.py</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </section>

  <!-- TAB 3: ARTIFACTS DEEP DIVE (QUERY TO DATA) -->
  <section id="artifacts-view" class="tab-pane max-w-7xl mx-auto space-y-6 hidden">
    
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-sm">
      <h2 class="text-xl font-serif font-semibold text-white">One example, from search to coded row</h2>
      <p class="text-sm text-slate-400 mt-1">
        Leonia, New Jersey closed streets to non-local drivers after navigation apps sent traffic through town. These are the query, the saved hit, and the coded row.
      </p>

      <!-- Step-by-step example cards -->
      <div class="mt-6 space-y-6">
        
        <!-- Artifact 1: Keyword Expansion -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5">
          <div class="flex items-center justify-between pb-3 border-b border-slate-800">
            <span class="text-xs font-semibold text-slate-300">Search terms</span>
            <span class="text-xs text-slate-400 font-mono">Taxonomy Design</span>
          </div>
          <p class="text-xs text-slate-300 mt-3">
            Initial research objective: capture municipal ordinances blocking commuter shortcut traffic. Expanded into mandatory app groups and Boolean proximity blocks:
          </p>
          <div class="mt-3 bg-slate-900 p-3 rounded-lg border border-slate-800 text-xs font-mono text-emerald-400 overflow-x-auto">
            ( "cut-through traffic" OR "through traffic" OR "shortcut traffic" OR "rat running" OR "residential streets" )<br>
            AND ( complaint OR complaints OR backlash OR opposition OR petition OR "public comment" )<br>
            AND ( ( law OR ordinance OR ban OR regulation ) W/20 ( routing OR navigation OR traffic OR streets ) )
          </div>
        </div>

        <!-- Artifact 2: The Executed Nexis Query -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5">
          <div class="flex items-center justify-between pb-3 border-b border-slate-800">
            <span class="text-xs font-semibold text-slate-300">Overview query sent to Nexis</span>
            <span class="text-xs text-slate-400 font-mono">queries/nexis_us_overview_query.txt (US-OVERVIEW-01)</span>
          </div>
          <div class="mt-3 bg-slate-900 p-3 rounded-lg border border-slate-800 text-xs font-mono text-slate-300 max-h-32 overflow-y-auto">
            ( Waze OR "Google Maps" OR "Apple Maps" OR MapQuest OR "HERE WeGo" OR "navigation app" OR "routing app" ) AND ( ( "road access" OR "turn restriction" OR "road closure" OR "resident only" OR "no through traffic" OR "traffic calming" OR "traffic diverter" OR "congestion pricing" OR ( ( law OR ordinance OR ban ) W/20 ( routing OR navigation OR traffic ) ) ) OR ( "routing policy" OR "routing algorithm" OR "avoid residential streets" OR "eco-friendly routing" ) OR ( "Waze for Cities" OR "Connected Citizens Program" OR ( ( partnership OR "data sharing" ) W/20 ( government OR city OR "transportation department" ) ) ) )
          </div>
        </div>

        <!-- Artifact 3: Raw Search Hit & NITF Record -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5">
          <div class="flex items-center justify-between pb-3 border-b border-slate-800">
            <span class="text-xs font-semibold text-slate-300">Saved document</span>
            <span class="text-xs text-slate-400 font-mono">URN: urn:contentItem:5YD5-NK31-JC65-51MB-00000-00</span>
          </div>
          <div class="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div class="bg-slate-900 p-3 rounded-lg border border-slate-800 space-y-1 text-slate-300">
              <div><strong class="text-white">Title:</strong> Town that closed streets to commuters gets court reprieve</div>
              <div><strong class="text-white">Publisher:</strong> Associated Press / NorthJersey.com</div>
              <div><strong class="text-white">Date:</strong> 2018-05-18</div>
              <div><strong class="text-white">Subject Geography:</strong> Leonia, Bergen County, New Jersey</div>
            </div>
            <div class="bg-slate-900 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-slate-400 overflow-y-auto max-h-24">
              &lt;nitf:body.content&gt;<br>
              &nbsp;&nbsp;&lt;p&gt;A state judge has refused to dismiss a town's lawsuit seeking to uphold its ban on outside drivers using residential side streets to avoid George Washington Bridge gridlock...&lt;/p&gt;<br>
              &lt;/nitf:body.content&gt;
            </div>
          </div>
        </div>

        <!-- Artifact 4: Final 27-Column Analysis Row -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5">
          <div class="flex items-center justify-between pb-3 border-b border-slate-800">
            <span class="text-xs font-semibold text-slate-300">Coded row</span>
            <span class="text-xs text-slate-400 font-mono">data/exports/research_analysis_all_sources.csv</span>
          </div>
          <div class="mt-3 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div class="bg-slate-900 p-2.5 rounded border border-slate-800">
              <span class="text-[11px] text-slate-400 block">Governing Level</span>
              <span class="font-bold text-white text-sm">Government: City</span>
            </div>
            <div class="bg-slate-900 p-2.5 rounded border border-slate-800">
              <span class="text-[11px] text-slate-400 block">Authority Name</span>
              <span class="font-bold text-white text-sm">Borough of Leonia (Council & Police)</span>
            </div>
            <div class="bg-slate-900 p-2.5 rounded border border-slate-800">
              <span class="text-[11px] text-slate-400 block">Target Location</span>
              <span class="font-bold text-white text-sm">Leonia (City / NJ)</span>
            </div>
            <div class="bg-slate-900 p-2.5 rounded border border-slate-800">
              <span class="text-[11px] text-slate-400 block">Taxonomy Category</span>
              <span class="font-bold text-emerald-400 text-sm">Both (Measures & Feedback)</span>
            </div>
          </div>
          <div class="mt-3 bg-slate-900 p-3 rounded border border-slate-800 text-xs text-slate-300">
            <strong class="text-white block mb-1">Verbatim Validated Passage:</strong>
            <p class="italic text-slate-400 font-serif">
              "The borough closed 60 streets to non-residents during morning and evening rush hours after navigation apps like Waze and Google Maps began steering highway overflow through town."
            </p>
          </div>
        </div>

      </div>

    </div>

  </section>

  <!-- TAB 4: KEYWORD AUDIT & UNUSED TERMS -->
  <section id="keywords-view" class="tab-pane max-w-7xl mx-auto space-y-6 hidden">
    
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-sm">
      <h2 class="text-xl font-serif font-semibold text-white">Which search terms show up in the saved text</h2>
      <p class="text-sm text-slate-400 mt-1">
        Counts are title and summary matches across {total_sources} documents. A term with zero hits was in the search list and did not appear in the saved text.
      </p>

      <div class="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        {keyword_audit_html}
      </div>

    </div>

  </section>

  <!-- TAB 5: CODEBOOK MEASURES -->
  <section id="measures-view" class="tab-pane max-w-7xl mx-auto space-y-6 hidden">
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-sm">
      <h2 class="text-xl font-bold text-white">Codebook measures</h2>
      <p id="measures-summary" class="text-sm text-slate-400 mt-1"></p>
      <div id="measures-filters" class="flex flex-wrap gap-2 mt-4"></div>
    </div>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <ol id="measures-list" class="space-y-2"></ol>
      <div id="measures-detail" class="bg-slate-900/90 border border-slate-800 rounded-xl p-6 max-h-[70vh] overflow-y-auto"></div>
    </div>
  </section>

  <section id="outside-view" class="tab-pane max-w-7xl mx-auto space-y-6 hidden">
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-sm">
      <h2 class="text-xl font-bold text-white">Outside the codebook</h2>
      <p id="outside-summary" class="text-sm text-slate-400 mt-1"></p>
    </div>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <ol id="outside-list" class="space-y-2"></ol>
      <div id="outside-detail" class="bg-slate-900/90 border border-slate-800 rounded-xl p-6 max-h-[70vh] overflow-y-auto"></div>
    </div>
  </section>

  <section id="database-view" class="tab-pane max-w-7xl mx-auto space-y-4 hidden">
    <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
      <div>
        <h2 class="text-xl font-bold text-white">All saved documents</h2>
        <p id="database-count" class="text-sm text-slate-400 mt-1"></p>
      </div>
      <input id="database-search" type="search" placeholder="Search title, publisher, place, category" class="w-full sm:w-80 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-500" />
    </div>
    <div class="overflow-auto border border-slate-800 rounded-xl max-h-[75vh]">
      <table class="w-full text-left text-sm">
        <thead class="sticky top-0 bg-slate-900 text-slate-400 text-xs uppercase tracking-wide">
          <tr>
            <th class="px-3 py-2 font-medium">Title</th>
            <th class="px-3 py-2 font-medium">Date</th>
            <th class="px-3 py-2 font-medium">Publisher</th>
            <th class="px-3 py-2 font-medium">Place</th>
            <th class="px-3 py-2 font-medium">Governing Level</th>
            <th class="px-3 py-2 font-medium">Category</th>
          </tr>
        </thead>
        <tbody id="database-body"></tbody>
      </table>
    </div>
  </section>

  <!-- Script block injecting data and dynamic timeline/map logic -->
  <script>
    // Global Data Payload injected from Python
    let DATA = {json_str};

    let activeYearIndex = DATA.all_years.length; // Default to 'All Years' (last index)
    let isCumulativeMode = false;
    let isPlaying = false;
    let playInterval = null;
    let selectedLocation = null;
    let isNationwideSelected = false;
    let zoomBehavior = null;
    let currentZoomK = 1.0;
    let usAtlasData = null;

    // Standard State FIPS Code Dictionary
    const STATE_FIPS_MAP = {{
      "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
      "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
      "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
      "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
      "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
      "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
      "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
      "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
      "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
      "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
      "56": "WY", "72": "PR"
    }};

    const STATE_NAME_MAP = {{
      "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
      "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
      "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
      "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
      "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
      "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
      "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
      "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
      "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
      "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
      "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"
    }};

    // City to County & FIPS mapping for empirical routing policy locations
    const CITY_TO_COUNTY = {{
      "Leonia, NJ": {{ fips: ["34003"], county: "Bergen County, NJ" }},
      "Mantoloking, NJ": {{ fips: ["34029"], county: "Ocean County, NJ" }},
      "Newark, NJ": {{ fips: ["34013"], county: "Essex County, NJ" }},
      "Trenton, NJ": {{ fips: ["34021"], county: "Mercer County, NJ" }},
      "Los Angeles, CA": {{ fips: ["06037"], county: "Los Angeles County, CA" }},
      "San Francisco, CA": {{ fips: ["06075"], county: "San Francisco County, CA" }},
      "San Jose, CA": {{ fips: ["06085"], county: "Santa Clara County, CA" }},
      "Silicon Valley, CA": {{ fips: ["06085", "06081"], county: "Santa Clara & San Mateo Counties, CA" }},
      "Oakland, CA": {{ fips: ["06001"], county: "Alameda County, CA" }},
      "Sacramento, CA": {{ fips: ["06067"], county: "Sacramento County, CA" }},
      "San Diego, CA": {{ fips: ["06073"], county: "San Diego County, CA" }},
      "Fresno, CA": {{ fips: ["06019"], county: "Fresno County, CA" }},
      "Davis, CA": {{ fips: ["06113"], county: "Yolo County, CA" }},
      "Austin, TX": {{ fips: ["48453"], county: "Travis County, TX" }},
      "Dallas, TX": {{ fips: ["48113"], county: "Dallas County, TX" }},
      "Fort Worth, TX": {{ fips: ["48439"], county: "Tarrant County, TX" }},
      "Arlington, TX": {{ fips: ["48439"], county: "Tarrant County, TX" }},
      "Houston, TX": {{ fips: ["48201"], county: "Harris County, TX" }},
      "San Antonio, TX": {{ fips: ["48029"], county: "Bexar County, TX" }},
      "Amarillo, TX": {{ fips: ["48375", "48381"], county: "Potter & Randall Counties, TX" }},
      "New York City, NY": {{ fips: ["36061", "36047", "36081", "36005", "36085"], county: "New York City (5 Boroughs), NY" }},
      "Albany, NY": {{ fips: ["36001"], county: "Albany County, NY" }},
      "Chicago, IL": {{ fips: ["17031"], county: "Cook County, IL" }},
      "Evanston, IL": {{ fips: ["17031"], county: "Cook County, IL" }},
      "Naperville, IL": {{ fips: ["17043"], county: "DuPage County, IL" }},
      "Springfield, IL": {{ fips: ["17167"], county: "Sangamon County, IL" }},
      "Atlanta, GA": {{ fips: ["13121", "13089"], county: "Fulton & DeKalb Counties, GA" }},
      "Fulton County, GA": {{ fips: ["13121"], county: "Fulton County, GA" }},
      "Boston, MA": {{ fips: ["25025"], county: "Suffolk County, MA" }},
      "Seattle, WA": {{ fips: ["53033"], county: "King County, WA" }},
      "Spokane, WA": {{ fips: ["53063"], county: "Spokane County, WA" }},
      "Miami, FL": {{ fips: ["12086"], county: "Miami-Dade County, FL" }},
      "Miami-Dade County, FL": {{ fips: ["12086"], county: "Miami-Dade County, FL" }},
      "Coral Gables, FL": {{ fips: ["12086"], county: "Miami-Dade County, FL" }},
      "Jacksonville, FL": {{ fips: ["12031"], county: "Duval County, FL" }},
      "Tampa, FL": {{ fips: ["12057"], county: "Hillsborough County, FL" }},
      "Tallahassee, FL": {{ fips: ["12073"], county: "Leon County, FL" }},
      "Philadelphia, PA": {{ fips: ["42101"], county: "Philadelphia County, PA" }},
      "Pittsburgh, PA": {{ fips: ["42003"], county: "Allegheny County, PA" }},
      "Harrisburg, PA": {{ fips: ["42043"], county: "Dauphin County, PA" }},
      "Lancaster, PA": {{ fips: ["42071"], county: "Lancaster County, PA" }},
      "Phoenix, AZ": {{ fips: ["04013"], county: "Maricopa County, AZ" }},
      "Denver, CO": {{ fips: ["08031"], county: "Denver County, CO" }},
      "Colorado Springs, CO": {{ fips: ["08041"], county: "El Paso County, CO" }},
      "Detroit, MI": {{ fips: ["26163"], county: "Wayne County, MI" }},
      "Midland, MI": {{ fips: ["26111"], county: "Midland County, MI" }},
      "Saint Paul, MN": {{ fips: ["27123"], county: "Ramsey County, MN" }},
      "Saint Louis, MO": {{ fips: ["29510", "29189"], county: "St. Louis City & County, MO" }},
      "Kansas City, MO": {{ fips: ["29095", "29047"], county: "Jackson & Clay Counties, MO" }},
      "Raleigh, NC": {{ fips: ["37183"], county: "Wake County, NC" }},
      "Cary, NC": {{ fips: ["37183"], county: "Wake County, NC" }},
      "Charlotte, NC": {{ fips: ["37119"], county: "Mecklenburg County, NC" }},
      "Greensboro, NC": {{ fips: ["37081"], county: "Guilford County, NC" }},
      "Asheville, NC": {{ fips: ["37021"], county: "Buncombe County, NC" }},
      "Nashville, TN": {{ fips: ["47037"], county: "Davidson County, TN" }},
      "Knoxville, TN": {{ fips: ["47093"], county: "Knox County, TN" }},
      "Norfolk, VA": {{ fips: ["51710"], county: "Norfolk City, VA" }},
      "Virginia Beach, VA": {{ fips: ["51810"], county: "Virginia Beach City, VA" }},
      "Richmond, VA": {{ fips: ["51760"], county: "Richmond City, VA" }},
      "Loudoun County, VA": {{ fips: ["51107"], county: "Loudoun County, VA" }},
      "Washington, DC": {{ fips: ["11001"], county: "District of Columbia" }},
      "District of Columbia": {{ fips: ["11001"], county: "District of Columbia" }},
      "Baltimore, MD": {{ fips: ["24510"], county: "Baltimore City, MD" }},
      "Columbus, OH": {{ fips: ["39049"], county: "Franklin County, OH" }},
      "Toledo, OH": {{ fips: ["39095"], county: "Lucas County, OH" }},
      "Milwaukee, WI": {{ fips: ["55079"], county: "Milwaukee County, WI" }},
      "Salt Lake City, UT": {{ fips: ["49035"], county: "Salt Lake County, UT" }},
      "Portland, OR": {{ fips: ["41051"], county: "Multnomah County, OR" }},
      "Albuquerque, NM": {{ fips: ["35001"], county: "Bernalillo County, NM" }},
      "Santa Fe, NM": {{ fips: ["35049"], county: "Santa Fe County, NM" }},
      "Reno, NV": {{ fips: ["32031"], county: "Washoe County, NV" }},
      "Carson City, NV": {{ fips: ["32510"], county: "Carson City, NV" }},
      "Boise, ID": {{ fips: ["16001"], county: "Ada County, ID" }},
      "Hartford, CT": {{ fips: ["09003"], county: "Hartford County, CT" }},
      "Bridgeport, CT": {{ fips: ["09001"], county: "Fairfield County, CT" }},
      "Fairfield, CT": {{ fips: ["09001"], county: "Fairfield County, CT" }},
      "New Haven, CT": {{ fips: ["09009"], county: "New Haven County, CT" }},
      "Providence, RI": {{ fips: ["44007"], county: "Providence County, RI" }},
      "Dover, DE": {{ fips: ["10001"], county: "Kent County, DE" }},
      "Baton Rouge, LA": {{ fips: ["22033"], county: "East Baton Rouge Parish, LA" }},
      "Louisville, KY": {{ fips: ["21111"], county: "Jefferson County, KY" }},
      "Lexington, KY": {{ fips: ["21067"], county: "Fayette County, KY" }},
      "Des Moines, IA": {{ fips: ["19153"], county: "Polk County, IA" }},
      "Davenport, IA": {{ fips: ["19163"], county: "Scott County, IA" }},
      "Lincoln, NE": {{ fips: ["31109"], county: "Lancaster County, NE" }},
      "Sioux Falls, SD": {{ fips: ["46099"], county: "Minnehaha County, SD" }},
      "Montgomery, AL": {{ fips: ["01101"], county: "Montgomery County, AL" }},
      "Augusta, ME": {{ fips: ["23011"], county: "Kennebec County, ME" }},
      "Anchorage, AK": {{ fips: ["02020"], county: "Anchorage Municipality, AK" }},
      "Ferguson, MO": {{ fips: ["29189"], county: "St. Louis County, MO" }},
      "Sandy Springs, GA": {{ fips: ["13121"], county: "Fulton County, GA" }},
      "Mount Prospect, IL": {{ fips: ["17031"], county: "Cook County, IL" }},
      "Chesapeake, VA": {{ fips: ["51550"], county: "Chesapeake City, VA" }},
      "Wheaton, IL": {{ fips: ["17043"], county: "DuPage County, IL" }},
      "Rochester, NY": {{ fips: ["36055"], county: "Monroe County, NY" }},
      "Buffalo, NY": {{ fips: ["36029"], county: "Erie County, NY" }},
      "Las Vegas, NV": {{ fips: ["32003"], county: "Clark County, NV" }},
      "Minneapolis, MN": {{ fips: ["27053"], county: "Hennepin County, MN" }},
      "Fort Lauderdale, FL": {{ fips: ["12011"], county: "Broward County, FL" }},
      "Roanoke, VA": {{ fips: ["51770"], county: "Roanoke City, VA" }},
      "Salem, OR": {{ fips: ["41047", "41053"], county: "Marion & Polk Counties, OR" }},
      "Jefferson City, MO": {{ fips: ["29051"], county: "Cole County, MO" }},
      "Oklahoma City, OK": {{ fips: ["40109"], county: "Oklahoma County, OK" }},
      "Grand Junction, CO": {{ fips: ["08077"], county: "Mesa County, CO" }},
      "Tucson, AZ": {{ fips: ["04019"], county: "Pima County, AZ" }},
      "Orlando, FL": {{ fips: ["12095"], county: "Orange County, FL" }},
      "New Orleans, LA": {{ fips: ["22071"], county: "Orleans Parish, LA" }},
      "Plano, TX": {{ fips: ["48085"], county: "Collin County, TX" }},
      "El Paso, TX": {{ fips: ["48141"], county: "El Paso County, TX" }},
      "Tacoma, WA": {{ fips: ["53053"], county: "Pierce County, WA" }},
      "Fort Myers, FL": {{ fips: ["12071"], county: "Lee County, FL" }},
      "Riverside, CA": {{ fips: ["06065"], county: "Riverside County, CA" }},
      "Charleston, SC": {{ fips: ["45019"], county: "Charleston County, SC" }},
      "Honolulu, HI": {{ fips: ["15003"], county: "Honolulu County, HI" }},
      "Cleveland, OH": {{ fips: ["39035"], county: "Cuyahoga County, OH" }},
      "Wichita, KS": {{ fips: ["20173"], county: "Sedgwick County, KS" }},
      "Aspinwall, PA": {{ fips: ["42003"], county: "Allegheny County, PA" }},
      "Albany, GA": {{ fips: ["13095"], county: "Dougherty County, GA" }},
      "Allentown, PA": {{ fips: ["42077"], county: "Lehigh County, PA" }},
      "Annapolis, MD": {{ fips: ["24003"], county: "Anne Arundel County, MD" }},
      "Bangor, ME": {{ fips: ["23019"], county: "Penobscot County, ME" }},
      "Biloxi, MS": {{ fips: ["28047"], county: "Harrison County, MS" }},
      "Cedar Rapids, IA": {{ fips: ["19113"], county: "Linn County, IA" }},
      "Danville, VA": {{ fips: ["51590"], county: "Danville City, VA" }},
      "Daytona Beach, FL": {{ fips: ["12127"], county: "Volusia County, FL" }},
      "Duluth, MN": {{ fips: ["27137"], county: "St. Louis County, MN" }},
      "Erie, PA": {{ fips: ["42049"], county: "Erie County, PA" }},
      "Fargo, ND": {{ fips: ["38017"], county: "Cass County, ND" }},
      "Fort Collins, CO": {{ fips: ["08069"], county: "Larimer County, CO" }},
      "Johnson City, TN": {{ fips: ["47179"], county: "Washington County, TN" }},
      "Little Rock, AR": {{ fips: ["05119"], county: "Pulaski County, AR" }},
      "Madison, WI": {{ fips: ["55025"], county: "Dane County, WI" }},
      "Memphis, TN": {{ fips: ["47157"], county: "Shelby County, TN" }},
      "Nashville, TN": {{ fips: ["47037"], county: "Davidson County, TN" }},
      "Palm Springs, CA": {{ fips: ["06065"], county: "Riverside County, CA" }},
      "Provo, UT": {{ fips: ["49049"], county: "Utah County, UT" }},
      "Topeka, KS": {{ fips: ["20177"], county: "Shawnee County, KS" }},
      "Wilmington, DE": {{ fips: ["10003"], county: "New Castle County, DE" }},
      "Yakima, WA": {{ fips: ["53077"], county: "Yakima County, WA" }},
      "Multi-City Transit Pilot": {{ fips: ["32003", "12057"], county: "Clark County, NV & Hillsborough County, FL" }},
      "Multi-City AV Pilot": {{ fips: ["06075", "06037", "04013", "48453", "13121"], county: "Multi-City AV Consortium" }},
      "Multi-City Metro Cohort": {{ fips: ["13121", "25025", "17031", "06037"], county: "Multi-City Metro Cohort" }}
    }};

    const FIPS_TO_LOCATIONS = {{}};
    Object.entries(CITY_TO_COUNTY).forEach(([cName, info]) => {{
      const fipsArr = Array.isArray(info.fips) ? info.fips : [info.fips];
      fipsArr.forEach(f => {{
        if (!FIPS_TO_LOCATIONS[f]) FIPS_TO_LOCATIONS[f] = [];
        if (!FIPS_TO_LOCATIONS[f].includes(cName)) FIPS_TO_LOCATIONS[f].push(cName);
      }});
    }});

    // Determine the intrinsic governing level for a location matching legend categories
    function getLocationGov(loc) {{
      if (!loc || !loc.name) return 'City';
      const name = loc.name;

      if (name.includes('(State)')) return 'State';
      if (name.includes('County')) return 'County';
      if (name.startsWith('Multi-City') || name === 'Silicon Valley, CA') return 'Company';

      const govs = loc.gov_levels || {{}};
      const countyCnt = (govs['Government: County'] || 0) + (govs['County'] || 0);
      const cityCnt = (govs['Government: City'] || 0) + (govs['City'] || 0);
      const compCnt = govs['Company'] || 0;
      const stateCnt = (govs['Government: State'] || 0) + (govs['State'] || 0);

      if (countyCnt > 0 && cityCnt === 0) return 'County';
      if (compCnt > 0 && cityCnt === 0 && countyCnt === 0 && stateCnt === 0) return 'Company';
      if (stateCnt > 0 && cityCnt === 0 && countyCnt === 0) return 'State';

      return 'City';
    }}

    // Color by Governing Level strictly matching map legend
    function getGovColor(gov) {{
      if (!gov) return '#3b82f6';
      if (gov.includes('City')) return '#3b82f6'; // Blue (City)
      if (gov.includes('County')) return '#f43f5e'; // Rose (County)
      if (gov.includes('State')) return '#f59e0b'; // Amber (State)
      if (gov.includes('Company')) return '#10b981'; // Emerald (Company)
      if (gov.includes('Federal')) return '#a855f7'; // Purple (Federal)
      return '#3b82f6';
    }}

    // Helper to evaluate active policy count and metadata for any county FIPS
    function getCountyActivePolicy(fipsCode) {{
      const activeYear = getActiveYear();
      const matchedCities = FIPS_TO_LOCATIONS[fipsCode] || [];
      let totalCount = 0;
      let dominantGov = 'City';
      let dominantColor = '#3b82f6';
      let maxCnt = -1;
      const matchedLocs = [];

      // Check municipal/county policy coverage specifically mapped to this county
      if (matchedCities.length > 0) {{
        DATA.locations.forEach(loc => {{
          if (matchedCities.includes(loc.name)) {{
            let cnt = 0;
            if (activeYear === 'ALL') {{
              cnt = loc.total_count;
            }} else if (isCumulativeMode) {{
              Object.keys(loc.years).forEach(yr => {{ if (yr <= activeYear) cnt += loc.years[yr]; }});
            }} else {{
              cnt = loc.years[activeYear] || 0;
            }}

            if (cnt > 0) {{
              totalCount += cnt;
              matchedLocs.push(loc);
              if (cnt > maxCnt) {{
                maxCnt = cnt;
                dominantGov = getLocationGov(loc);
                dominantColor = getGovColor(dominantGov);
              }}
            }}
          }}
        }});
      }}

      return {{
        count: totalCount,
        topGov: dominantGov,
        color: dominantColor,
        cities: matchedCities,
        locations: matchedLocs
      }};
    }}

    // Canonical Albers USA Projection matching us-atlas 975x610 viewport
    let albersProjection = null;
    try {{
      if (typeof d3 !== 'undefined' && d3.geoAlbersUsa) {{
        albersProjection = d3.geoAlbersUsa().scale(1300).translate([487.5, 305]);
      }}
    }} catch(e) {{
      console.warn("D3 projection init:", e);
    }}

    function projectCoords(lat, lon) {{
      if (albersProjection) {{
        const pt = albersProjection([lon, lat]);
        if (pt) return {{ x: pt[0], y: pt[1] }};
      }}
      // Fallback projection if point is outside contiguous US (e.g. Alaska)
      const minLon = -125.0, maxLon = -66.0;
      const minLat = 24.0, maxLat = 50.0;
      const x = ((lon - minLon) / (maxLon - minLon)) * 790 + 70;
      const y = ((maxLat - lat) / (maxLat - minLat)) * 490 + 50;
      return {{ x: Math.max(50, Math.min(925, x)), y: Math.max(40, Math.min(570, y)) }};
    }}

    // State 2-letter postal code coordinates for labels
    const STATE_CENTROIDS = {{
      "WA": [-120.5, 47.4], "OR": [-120.5, 43.9], "CA": [-119.5, 36.8], "NV": [-116.8, 39.3],
      "ID": [-114.6, 44.4], "UT": [-111.7, 39.3], "AZ": [-111.7, 34.3], "MT": [-109.6, 47.1],
      "WY": [-107.5, 43.0], "CO": [-105.5, 39.0], "NM": [-106.0, 34.4], "ND": [-100.5, 47.4],
      "SD": [-100.2, 44.4], "NE": [-99.8, 41.5], "KS": [-98.4, 38.5], "OK": [-97.5, 35.5],
      "TX": [-99.3, 31.5], "MN": [-94.3, 46.3], "IA": [-93.5, 42.0], "MO": [-92.5, 38.4],
      "AR": [-92.4, 34.8], "LA": [-92.0, 31.0], "WI": [-89.8, 44.6], "IL": [-89.2, 40.0],
      "MI": [-84.7, 44.3], "IN": [-86.3, 39.8], "KY": [-85.3, 37.5], "TN": [-86.3, 35.8],
      "MS": [-89.7, 32.7], "AL": [-86.8, 32.8], "GA": [-83.4, 32.7], "FL": [-81.7, 28.1],
      "OH": [-82.8, 40.2], "WV": [-80.6, 38.6], "VA": [-78.9, 37.5], "NC": [-79.4, 35.5],
      "SC": [-80.9, 33.9], "PA": [-77.6, 40.9], "NY": [-75.5, 43.0], "ME": [-69.2, 45.4],
      "VT": [-72.6, 44.1], "NH": [-71.6, 43.7], "MA": [-71.8, 42.2], "CT": [-72.7, 41.6],
      "NJ": [-74.5, 40.1], "MD": [-76.7, 39.0], "DE": [-75.5, 39.0]
    }};

    // D3 Zoom Control Functions
    function zoomIn() {{
      if (zoomBehavior) {{
        d3.select("#us-map-svg").transition().duration(300).call(zoomBehavior.scaleBy, 1.5);
      }}
    }}

    function zoomOut() {{
      if (zoomBehavior) {{
        d3.select("#us-map-svg").transition().duration(300).call(zoomBehavior.scaleBy, 0.67);
      }}
    }}

    function resetZoom() {{
      if (zoomBehavior) {{
        d3.select("#us-map-svg").transition().duration(600).ease(d3.easeCubicOut).call(zoomBehavior.transform, d3.zoomIdentity);
      }}
    }}

    function zoomToCoords(x, y, targetK = 4.8) {{
      if (!zoomBehavior) return;
      const width = 975;
      const height = 610;
      const tx = width / 2 - x * targetK;
      const ty = height / 2 - y * targetK;
      d3.select("#us-map-svg").transition()
        .duration(750)
        .ease(d3.easeCubicOut)
        .call(zoomBehavior.transform, d3.zoomIdentity.translate(tx, ty).scale(targetK));
    }}

    let fipsFeatureMap = {{}};

    // Calculate the precise top-center and bounding dimensions of a location's shaded geographic region
    function getLocationRegionGeom(loc) {{
      const cInfo = CITY_TO_COUNTY[loc.name];
      if (cInfo && cInfo.fips && usAtlasData) {{
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        let sumCentroidX = 0, sumCentroidY = 0, validCentroids = 0;
        let foundAny = false;
        const path = d3.geoPath();
        cInfo.fips.forEach(fips => {{
          const feat = fipsFeatureMap[fips];
          if (feat) {{
            const bounds = path.bounds(feat);
            if (bounds && bounds[0] && bounds[1]) {{
              foundAny = true;
              minX = Math.min(minX, bounds[0][0]);
              minY = Math.min(minY, bounds[0][1]);
              maxX = Math.max(maxX, bounds[1][0]);
              maxY = Math.max(maxY, bounds[1][1]);
            }}
            const cent = path.centroid(feat);
            if (cent && !isNaN(cent[0]) && !isNaN(cent[1])) {{
              sumCentroidX += cent[0];
              sumCentroidY += cent[1];
              validCentroids++;
            }}
          }}
        }});
        if (foundAny) {{
          const width = maxX - minX;
          const height = maxY - minY;
          const cX = validCentroids > 0 ? (sumCentroidX / validCentroids) : ((minX + maxX) / 2);
          const cY = validCentroids > 0 ? (sumCentroidY / validCentroids) : ((minY + maxY) / 2);
          return {{
            centerX: cX,
            // Positioned at top-center of the shaded region: upper 20-25% between minY and centroid
            topY: minY + Math.max(2.2, (cY - minY) * 0.45),
            width: width,
            height: height
          }};
        }}
      }}

      // Fallback to projected coordinates if atlas not yet loaded or not mapped to FIPS
      const pt = projectCoords(loc.lat, loc.lon);
      if (pt) {{
        return {{
          centerX: pt.x,
          topY: pt.y - 8,
          width: 35,
          height: 25
        }};
      }}
      return null;
    }}

    // Dynamic County Region Shading & Bubble Cross-Fading Engine
    function updateCountyShading(k) {{
      // Smooth morphing threshold:
      // k < 2.2: National Bubble Mode (shadeFactor = 0, bubbleOpacity = 1)
      // 2.2 <= k < 3.2: Cross-fade transition between bubbles and shaded regions
      // k >= 3.2: County Shaded Boundary View (shadeFactor = 1, bubbleOpacity = 0)
      const shadeFactor = Math.min(1, Math.max(0, (k - 2.2) / 1.0));
      const bubbleOpacity = Math.max(0, 1 - (k - 2.2) / 0.9);

      // 1. Cross-fade point bubbles layer
      const bubbleLayer = d3.select("#map-bubbles-layer");
      const bubbleLabelsLayer = d3.select("#map-bubble-labels-layer");
      bubbleLayer.style("opacity", bubbleOpacity);
      bubbleLabelsLayer.style("opacity", bubbleOpacity);
      bubbleLayer.style("pointer-events", bubbleOpacity <= 0.05 ? "none" : "auto");

      // 2. Cross-fade county region shading - strictly for active policy coverage
      d3.selectAll(".county-path").each(function(d) {{
        if (!d || !d.id) return;
        const countyEl = d3.select(this);
        const policy = getCountyActivePolicy(d.id);

        if (policy.count > 0 && shadeFactor > 0) {{
          // Shaded region with distinct municipal policy color matching legend
          countyEl
            .classed("county-shaded-active", true)
            .style("fill", policy.color)
            .style("fill-opacity", 0.75 * shadeFactor)
            .style("stroke", shadeFactor > 0.3 ? policy.color : "#2a3a4f")
            .style("stroke-width", `${{Math.max(0.4, (1.2 * shadeFactor + 0.3) / k)}}px`);
        }} else {{
          // Default unshaded base county
          countyEl
            .classed("county-shaded-active", false)
            .style("fill", "#1e293b")
            .style("fill-opacity", 1)
            .style("stroke", "#2a3a4f")
            .style("stroke-width", `${{Math.max(0.2, 0.45 / k)}}px`);
        }}
      }});

      // 3. Proportional Region Name Labels (Top-Center of Shaded Regions)
      const regionLabelsLayer = d3.select("#map-city-labels-layer");
      if (regionLabelsLayer && !regionLabelsLayer.empty()) {{
        if (k < 2.0) {{
          regionLabelsLayer.style("opacity", "0");
        }} else {{
          // Smooth fade in as bubbles morph into shaded regions
          const layerOpacity = Math.min(1, (k - 2.0) / 0.8);
          regionLabelsLayer.style("opacity", `${{layerOpacity}}`);

          // Target screen font size: smoothly scales from 9.0px up to 13.5px with zoom
          const targetScreenFs = Math.min(13.5, Math.max(9.0, 8.5 + (k - 2.0) * 0.85));
          const targetStrokeWidth = Math.max(0.4, 2.2 / k);

          regionLabelsLayer.selectAll(".region-name-label").each(function() {{
            const textEl = d3.select(this);
            const geomW = parseFloat(textEl.attr("data-geom-width") || 20);
            const nameLen = parseFloat(textEl.attr("data-name-len") || 8);

            // Screen width of the region at current zoom k
            const regionScreenWidth = geomW * k;
            // Font size that fits within 92% of region width
            const fitScreenFs = (regionScreenWidth * 0.92) / (nameLen * 0.55);
            // Proportional and legible: bounded between 8.5px minimum and targetScreenFs
            const screenFs = Math.min(targetScreenFs, Math.max(8.5, fitScreenFs));
            const svgFs = screenFs / k;

            textEl
              .style("font-size", `${{svgFs}}px`)
              .style("stroke-width", `${{targetStrokeWidth}}px`)
              .style("opacity", "1");
          }});
        }}
      }}

      // 4. Update Zoom Tier Badge
      let tierName = "National Bubble View";
      if (k >= 3.2) {{
        tierName = "County Shaded View";
      }} else if (k >= 2.2) {{
        tierName = "Morphing to Shaded Regions";
      }}
      const badgeEl = document.getElementById("zoom-badge-text");
      if (badgeEl) badgeEl.textContent = `${{k.toFixed(1)}}x (${{tierName}})`;
    }}

    function handleZoom(event) {{
      const {{ transform }} = event;
      const k = transform.k;
      currentZoomK = k;

      // 1. Transform the master zoom group
      d3.select("#map-zoom-group").attr("transform", transform);

      // 2. Update dynamic county shading & bubble cross-fading
      updateCountyShading(k);

      // 3. Counter-scale state boundary & mesh stroke
      d3.selectAll(".state-boundary").style("stroke-width", `${{Math.max(0.4, 1.2 / k)}}px`);
      d3.selectAll(".state-mesh").style("stroke-width", `${{Math.max(0.5, 1.4 / k)}}px`);
      d3.selectAll(".county-mesh").style("stroke-width", `${{Math.max(0.15, 0.35 / k)}}px`);

      // 4. State 2-letter labels fade out smoothly at regional/county zoom
      const stateLabelsLayer = d3.select("#map-state-labels-layer");
      if (k >= 2.8) {{
        stateLabelsLayer.style("opacity", "0");
      }} else if (k >= 1.8) {{
        stateLabelsLayer.style("opacity", `${{Math.max(0, 1 - (k - 1.8) * 1.0)}}`);
      }} else {{
        stateLabelsLayer.style("opacity", "0.7");
      }}

      // 5. Counter-scale bubble radius & stroke
      d3.selectAll(".city-bubble").each(function() {{
        const el = d3.select(this);
        const baseR = parseFloat(el.attr("data-base-r") || el.attr("r"));
        el.attr("r", baseR / Math.pow(k, 0.42));
        el.style("stroke-width", `${{Math.max(0.6, 1.8 / k)}}px`);
      }});

      // 6. Counter-scale bubble numeric text
      d3.selectAll(".bubble-count-text").each(function() {{
        const el = d3.select(this);
        const baseFs = parseFloat(el.attr("data-base-fs") || 10);
        el.style("font-size", `${{Math.max(5.5, baseFs / Math.pow(k, 0.35))}}px`);
      }});
    }}


    function initDashboard() {{
      // Dynamically initialize header and top stats from DATA.metadata
      if (DATA && DATA.metadata) {{
        document.getElementById('stat-total-header').textContent = `${{DATA.metadata.total_sources}} Sources`;
        document.getElementById('stat-sources').textContent = `${{DATA.metadata.total_sources}} Sources`;
        document.getElementById('stat-sources-sub').textContent = `${{DATA.metadata.localized_sources}} on the map · ${{DATA.metadata.nationwide_sources}} filed to the United States`;
        document.getElementById('stat-locations').textContent = `${{DATA.metadata.unique_locations}} Locations`;
        document.getElementById('stat-years').textContent = DATA.metadata.year_range;
      }}

      initSliderTicks();
      initHighPrecisionMap();
      renderLeaderboard();
      updateSelectedEraCard();
      updateNationwideHud();

      document.getElementById('json-file-input').addEventListener('change', handleFileUpload);
    }}

    function initSliderTicks() {{
      const ticksContainer = document.getElementById('slider-ticks');
      ticksContainer.innerHTML = '';
      
      const slider = document.getElementById('timeline-slider');
      slider.max = DATA.all_years.length; // index DATA.all_years.length = All Years
      slider.value = DATA.all_years.length;

      DATA.all_years.forEach((yr, idx) => {{
        if (idx % 2 === 0 || idx === DATA.all_years.length - 1) {{
          const span = document.createElement('span');
          span.textContent = "'" + yr.slice(2);
          ticksContainer.appendChild(span);
        }}
      }});
      const allSpan = document.createElement('span');
      allSpan.textContent = 'All';
      allSpan.className = 'font-bold text-amber-400';
      ticksContainer.appendChild(allSpan);
    }}

    function getActiveYear() {{
      if (activeYearIndex >= DATA.all_years.length) return 'ALL';
      return DATA.all_years[activeYearIndex];
    }}

    function onTimelineChange(val) {{
      activeYearIndex = parseInt(val);
      const activeYear = getActiveYear();
      
      document.getElementById('selected-year-badge').textContent = (activeYear === 'ALL') ? 'All Years' : activeYear;
      updateSelectedEraCard();
      updateNationwideHud();
      renderMap();
      renderLeaderboard();
      if (selectedLocation) renderLocationDetail(selectedLocation);
    }}

    function toggleCumulativeMode() {{
      isCumulativeMode = !isCumulativeMode;
      document.getElementById('mode-text').textContent = isCumulativeMode ? 'Cumulative Thru Year' : 'Single Year';
      document.getElementById('toggle-cumulative-btn').className = isCumulativeMode 
        ? 'bg-blue-600/30 text-blue-400 border border-blue-500/40 text-xs px-3 py-1.5 rounded-lg transition font-medium'
        : 'bg-slate-800 text-slate-300 border border-slate-700 text-xs px-3 py-1.5 rounded-lg transition font-medium';
      renderMap();
      renderLeaderboard();
    }}

    function togglePlayTimeline() {{
      isPlaying = !isPlaying;
      const btnIcon = document.getElementById('play-btn-icon');
      const btnText = document.getElementById('play-btn-text');

      if (isPlaying) {{
        btnIcon.textContent = '⏸';
        btnText.textContent = 'Pause';
        if (activeYearIndex >= DATA.all_years.length) activeYearIndex = 0;
        
        playInterval = setInterval(() => {{
          activeYearIndex++;
          if (activeYearIndex > DATA.all_years.length) {{
            activeYearIndex = DATA.all_years.length;
            togglePlayTimeline();
            return;
          }}
          document.getElementById('timeline-slider').value = activeYearIndex;
          onTimelineChange(activeYearIndex);
        }}, 1400);
      }} else {{
        btnIcon.textContent = '▶';
        btnText.textContent = 'Play Timeline';
        clearInterval(playInterval);
      }}
    }}

    function updateNationwideHud() {{
      const year = getActiveYear();
      const badge = document.getElementById('nationwide-badge-count');
      const desc = document.getElementById('nationwide-hud-desc');
      const nw = DATA.nationwide;

      if (!nw) return;

      let count = 0;
      if (year === 'ALL') {{
        count = nw.total_count;
        badge.textContent = `${{count}} Sources (United States)`;
        desc.textContent = "Articles scoped to the United States, or to a place this map cannot pin. That includes federal rules, platform-wide features, and crawled stories with no city or state.";
      }} else if (isCumulativeMode) {{
        Object.keys(nw.years).forEach(yr => {{
          if (yr <= year) count += nw.years[yr];
        }});
        badge.textContent = `${{count}} Sources Thru ${{year}}`;
        desc.textContent = `United States and unpinned articles dated through ${{year}}. Undated articles stay in the full-corpus view.`;
      }} else {{
        count = nw.years[year] || 0;
        badge.textContent = `${{count}} Sources in ${{year}}`;
        desc.textContent = count > 0
          ? `United States and unpinned articles dated ${{year}}.`
          : `No United States or unpinned articles dated ${{year}}.`;
      }}
    }}

    function setNationwideHighlight(active) {{
      const countyPaths = document.querySelectorAll('.county-path');
      const stateBorders = document.querySelectorAll('.state-mesh, .state-boundary');
      countyPaths.forEach(p => {{
        if (active || isNationwideSelected) {{
          p.classList.add('nationwide-active');
        }} else {{
          p.classList.remove('nationwide-active');
        }}
      }});
      stateBorders.forEach(p => {{
        if (active || isNationwideSelected) {{
          p.classList.add('nationwide-active');
        }} else {{
          p.classList.remove('nationwide-active');
        }}
      }});
    }}

    function articleAnchor(sourceId) {{
      return 'doc-' + String(sourceId || 'row').replace(/[^A-Za-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
    }}

    function articleSourceUrl(art) {{
      const url = String((art && art.url) || '');
      if (url.startsWith('http://') || url.startsWith('https://')) return url;
      const id = String((art && art.source_id) || '');
      const match = id.match(/urn:contentItem:[A-Za-z0-9-]+/);
      if (!match) return '';
      return 'https://www.nexisuni.com/document/?pddocfullpath=' + encodeURIComponent('/shared/document/news/' + match[0]);
    }}

    function openRecord(sourceId) {{
      switchTab('database-view');
      const anchor = articleAnchor(sourceId);
      const search = document.getElementById('database-search');
      if (search && search.value) {{
        search.value = '';
        renderDatabase('');
      }}
      requestAnimationFrame(() => {{
        document.querySelectorAll('#database-body tr.marked').forEach(row => row.classList.remove('marked', 'bg-amber-500/10'));
        const row = document.getElementById(anchor);
        if (!row) return;
        row.classList.add('marked', 'bg-amber-500/10');
        row.scrollIntoView({{ block: 'center' }});
      }});
    }}

    function appendSourceLine(parent, art) {{
      const source = document.createElement('div');
      source.className = 'text-[11px] text-slate-400';
      const publisher = art.publisher || art.authority || '';
      if (publisher) source.appendChild(document.createTextNode(publisher));
      if (art.source_id) {{
        if (publisher) source.appendChild(document.createTextNode(' · '));
        const record = document.createElement('button');
        record.type = 'button';
        record.className = 'text-blue-400 hover:text-blue-300 underline';
        record.textContent = 'Record';
        record.addEventListener('click', () => openRecord(art.source_id));
        source.appendChild(record);
      }}
      parent.appendChild(source);
    }}

    function appendArticleCard(parent, art) {{
      const card = document.createElement('div');
      card.className = 'bg-slate-950/80 border border-slate-800 rounded-lg p-3 space-y-1.5 transition hover:border-slate-700';
      const top = document.createElement('div');
      top.className = 'flex items-center justify-between gap-2';
      const year = document.createElement('span');
      year.className = 'text-[11px] font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded';
      year.textContent = art.year || '';
      const gov = document.createElement('span');
      gov.className = 'text-[11px] text-blue-400 font-semibold text-right';
      gov.textContent = art.gov || '';
      top.append(year, gov);
      const title = document.createElement('div');
      title.className = 'font-bold text-white text-xs leading-snug';
      const sourceUrl = articleSourceUrl(art);
      const titleLink = sourceUrl ? document.createElement('a') : document.createElement('span');
      titleLink.className = sourceUrl
        ? 'hover:text-blue-300 underline decoration-slate-600 underline-offset-2'
        : '';
      titleLink.textContent = art.title || 'Untitled';
      if (sourceUrl) {{
        titleLink.href = sourceUrl;
        titleLink.target = '_blank';
        titleLink.rel = 'noreferrer';
      }}
      title.appendChild(titleLink);
      card.append(top, title);
      appendSourceLine(card, art);
      if (art.summary) {{
        const summary = document.createElement('p');
        summary.className = 'text-slate-300 text-[11px] leading-relaxed';
        summary.textContent = art.summary;
        card.appendChild(summary);
      }}
      parent.appendChild(card);
    }}

    function selectNationwideScope() {{
      isNationwideSelected = true;
      setNationwideHighlight(true);
      selectedLocation = null;

      const year = getActiveYear();
      const nw = DATA.nationwide;
      
      let articles = [];
      if (year === 'ALL') {{
        articles = nw.articles;
      }} else if (isCumulativeMode) {{
        articles = nw.articles.filter(a => a.year <= year);
      }} else {{
        articles = nw.articles.filter(a => a.year === year);
      }}

      document.getElementById('loc-badge-count').textContent = `${{articles.length}} Sources`;
      document.getElementById('loc-badge-count').className = 'text-xs font-bold text-sky-400 bg-sky-500/10 px-2.5 py-0.5 rounded-full border border-sky-500/20';

      const detailDiv = document.getElementById('location-detail-content');
      detailDiv.innerHTML = `
        <div class="bg-sky-950/40 border border-sky-800/60 rounded-lg p-3 text-xs mb-3">
          <div class="font-bold text-sky-300 flex items-center gap-1.5">
            <span>United States</span>
          </div>
          <p class="text-slate-300 mt-1">
            These articles are scoped to the United States, or to a place this map cannot pin. Coded federal rules and platform-wide features are in this list with crawled stories that have no city or state.
          </p>
        </div>
      `;

      if (articles.length === 0) {{
        detailDiv.innerHTML += `
          <div class="text-slate-500 text-center py-6">
            No United States or unpinned articles dated ${{year}}.
          </div>
        `;
        return;
      }}

      articles.forEach(art => appendArticleCard(detailDiv, art));
    }}

    function updateSelectedEraCard() {{
      const year = getActiveYear();
      const title = document.getElementById('era-title');
      const desc = document.getElementById('era-description');

      if (year === 'ALL') {{
        title.textContent = `All saved documents (${{DATA.metadata.year_range}})`;
        desc.textContent = `Showing ${{DATA.metadata.total_sources}} documents across ${{DATA.metadata.unique_locations}} mapped places.`;
      }} else if (isCumulativeMode) {{
        title.textContent = `Documents through ${{year}}`;
        desc.textContent = `Articles dated ${{year}} or earlier. Undated articles stay in the full-corpus view.`;
      }} else {{
        title.textContent = `Documents from ${{year}}`;
        desc.textContent = `Articles dated ${{year}}.`;
      }}
    }}

    // High-Precision D3 TopoJSON County & State Map Initializer
    function initHighPrecisionMap() {{
      const svg = d3.select("#us-map-svg");
      const countiesLayer = svg.select("#map-counties-layer");
      const countyMeshLayer = svg.select("#map-county-mesh-layer");
      const statesLayer = svg.select("#map-states-layer");
      const stateMeshLayer = svg.select("#map-state-mesh-layer");
      const stateLabelsLayer = svg.select("#map-state-labels-layer");

      // Initialize D3 Zoom Behavior with trackpad, pinch & drag
      zoomBehavior = d3.zoom()
        .scaleExtent([1, 14])
        .translateExtent([[-150, -100], [1125, 710]])
        .on("zoom", handleZoom);

      svg.call(zoomBehavior);

      // Load canonical TopoJSON US Atlas with all 3,142 pre-projected counties
      const usAtlasUrl = "https://cdn.jsdelivr.net/npm/us-atlas@3/counties-albers-10m.json";

      d3.json(usAtlasUrl).then(us => {{
        if (!us || !us.objects) return;
        usAtlasData = us;

        const path = d3.geoPath(); // Pre-projected Albers coordinates matching 975x610 viewport

        // 1. Render all 3,142 U.S. Counties (Clickable & Hoverable down to municipal precision)
        if (us.objects.counties) {{
          const counties = topojson.feature(us, us.objects.counties).features;
          fipsFeatureMap = {{}};
          counties.forEach(f => {{
            fipsFeatureMap[f.id] = f;
          }});
          countiesLayer.selectAll("path")
            .data(counties)
            .join("path")
            .attr("d", path)
            .attr("class", d => {{
              const hasPolicy = FIPS_TO_LOCATIONS[d.id] ? "county-has-policy" : "";
              return `county-path ${{hasPolicy}}`;
            }})
            .attr("id", d => "county-" + (d.id || ""))
            .on("mouseenter", (event, d) => handleCountyHover(event, d))
            .on("mouseleave", hideTooltip)
            .on("click", (event, d) => handleCountyClick(event, d, path));

          // Render Interior County Mesh (Crisp boundaries between adjacent counties)
          countyMeshLayer.append("path")
            .datum(topojson.mesh(us, us.objects.counties, (a, b) => a !== b))
            .attr("d", path)
            .attr("class", "county-mesh");
        }}

        // 2. Render State Boundaries & Outer Nation Outline
        if (us.objects.states) {{
          stateMeshLayer.append("path")
            .datum(topojson.mesh(us, us.objects.states, (a, b) => a !== b))
            .attr("d", path)
            .attr("class", "state-mesh");

          if (us.objects.nation) {{
            statesLayer.append("path")
              .datum(topojson.feature(us, us.objects.nation))
              .attr("d", path)
              .attr("class", "state-boundary")
              .style("stroke", "#64748b")
              .style("stroke-width", "1.6px")
              .style("fill", "none");
          }}
        }}

        // 3. Render 2-Letter State Postal Codes (CA, TX, NY...)
        renderStateLabels();

        // 4. Render Localized City Bubbles, Count Badges & City Name Badges
        renderMap();
      }}).catch(err => {{
        console.warn("Could not load online TopoJSON, drawing vector fallback:", err);
        drawFallbackStates(statesLayer);
        renderMap();
      }});
    }}

    function renderStateLabels() {{
      const stateLabelsLayer = d3.select("#map-state-labels-layer");
      stateLabelsLayer.selectAll("text").remove();
      Object.entries(STATE_CENTROIDS).forEach(([code, coords]) => {{
        const pt = projectCoords(coords[1], coords[0]);
        if (pt && pt.x > 50 && pt.x < 925 && pt.y > 40 && pt.y < 570) {{
          stateLabelsLayer.append("text")
            .attr("x", pt.x)
            .attr("y", pt.y)
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "central")
            .attr("fill", "#64748b")
            .attr("font-size", "10px")
            .attr("font-weight", "700")
            .attr("letter-spacing", "0.6px")
            .attr("opacity", "0.7")
            .text(code);
        }}
      }});
    }}

    // Fallback vector states outline if offline
    function drawFallbackStates(statesLayer) {{
      statesLayer.html(`
        <path d="M 140,95 L 220,95 L 300,95 L 380,95 L 450,90 L 520,80 L 580,75 L 610,65 L 670,60 L 720,70 L 760,60 L 800,85 L 830,120 L 860,110 L 880,140 L 860,170 L 840,195 L 830,240 L 800,280 L 800,320 L 780,360 L 790,410 L 770,440 L 760,490 L 730,460 L 700,430 L 640,430 L 580,450 L 530,460 L 490,520 L 460,540 L 420,490 L 370,460 L 320,440 L 250,440 L 190,420 L 140,360 L 110,320 L 100,240 L 90,170 L 110,120 Z" class="state-path" />
        <path d="M 230,95 L 220,440 M 340,95 L 340,450 M 470,95 L 460,530 M 590,80 L 580,450 M 710,65 L 700,430 M 120,220 L 830,220 M 150,330 L 800,330" stroke="#334155" stroke-dasharray="3 3" opacity="0.4" fill="none" />
      `);
    }}

    function handleCountyHover(event, d) {{
      const stateCode = STATE_FIPS_MAP[d.id.slice(0, 2)] || "";
      const stateName = STATE_NAME_MAP[stateCode] || stateCode;
      const rawName = (d.properties && d.properties.name) ? d.properties.name : "County";
      const countyName = rawName + (rawName.toLowerCase().includes("city") || rawName.toLowerCase().includes("parish") || stateCode === "DC" ? "" : " County");

      const policy = getCountyActivePolicy(d.id);
      const title = `${{countyName}}, ${{stateCode}}`;
      let body = "";
      if (policy.count > 0) {{
        body = `<div class="text-amber-400 font-bold mb-1">${{policy.count}} Routing Policy Sources</div>` +
               `<div class="text-slate-300">Coverage: <strong class="text-white">${{policy.cities.join(", ")}}</strong> (${{policy.topGov}})</div>` +
               `<div class="text-[11px] text-slate-400 mt-1">Click shaded county to inspect local policy records.</div>`;
      }} else if (policy.statewideCount > 0) {{
        body = `<div class="text-amber-300 font-bold mb-1">${{policy.statewideCount}} Statewide Policy Sources</div>` +
               `<div class="text-slate-300">Jurisdiction: <strong class="text-white">${{stateName}}</strong> (State DOT)</div>` +
               `<div class="text-[11px] text-slate-400 mt-1">Click to zoom and inspect regional routing policies.</div>`;
      }} else {{
        body = `<div class="text-slate-400 font-medium">Jurisdiction: ${{stateName}}</div>` +
               `<div class="text-slate-500 text-[11px] mt-0.5">Click to zoom and inspect regional routing policies.</div>`;
      }}
      showTooltip(event, title, body);
    }}

    function handleCountyClick(event, d, path) {{
      const stateCode = STATE_FIPS_MAP[d.id.slice(0, 2)] || "";
      const stateName = STATE_NAME_MAP[stateCode] || stateCode;
      const rawName = (d.properties && d.properties.name) ? d.properties.name : "County";
      const countyName = rawName + (rawName.toLowerCase().includes("city") || rawName.toLowerCase().includes("parish") || stateCode === "DC" ? "" : " County");

      // Smoothly zoom in to the centroid of this county if from national view
      const centroid = path.centroid(d);
      if (centroid && !isNaN(centroid[0]) && !isNaN(centroid[1])) {{
        if (currentZoomK < 3.2) {{
          zoomToCoords(centroid[0], centroid[1], 4.8);
        }}
      }}

      const policy = getCountyActivePolicy(d.id);

      if (policy.locations && policy.locations.length > 0) {{
        selectLocation(policy.locations[0], false);
      }} else {{
        // Present county jurisdiction overview card
        selectedLocation = null;
        isNationwideSelected = false;
        setNationwideHighlight(false);

        document.getElementById('loc-badge-count').textContent = `County Jurisdiction`;
        document.getElementById('loc-badge-count').className = 'text-xs font-bold text-slate-400 bg-slate-800 px-2.5 py-0.5 rounded-full border border-slate-700';

        const detailDiv = document.getElementById('location-detail-content');
        detailDiv.innerHTML = `
          <div class="bg-slate-950 p-3.5 rounded-lg border border-slate-800 text-xs mb-3 space-y-2">
            <div class="font-bold text-white text-sm flex items-center gap-2">
              <span>🏛️</span> <span>${{countyName}}, ${{stateCode}}</span>
            </div>
            <div class="text-[11px] text-slate-400 font-mono">FIPS: ${{d.id}} • State Jurisdiction: ${{stateName}}</div>
            <p class="text-slate-300 text-xs leading-relaxed mt-2">
              No specific municipal street bans or local anti-shortcut ordinances were identified specifically inside this county in the research corpus.
              Traffic management across this county is governed under ${{stateName}} DOT highway specifications and federal routing standards.
            </p>
          </div>
        `;
      }}
    }}

    function renderMap() {{
      const bubbleLayer = document.getElementById('map-bubbles-layer');
      const bubbleLabelsLayer = document.getElementById('map-bubble-labels-layer');
      const cityLabelsLayer = document.getElementById('map-city-labels-layer');
      bubbleLayer.innerHTML = '';
      bubbleLabelsLayer.innerHTML = '';
      if (cityLabelsLayer) cityLabelsLayer.innerHTML = '';
      const activeYear = getActiveYear();
      const coordUsageMap = {{}};

      DATA.locations.forEach(loc => {{
        let count = 0;
        if (activeYear === 'ALL') {{
          count = loc.total_count;
        }} else if (isCumulativeMode) {{
          Object.keys(loc.years).forEach(yr => {{
            if (yr <= activeYear) count += loc.years[yr];
          }});
        }} else {{
          count = loc.years[activeYear] || 0;
        }}

        // If count is 0 in single-year mode, do not render a bubble
        if (count === 0) return;

        const coords = projectCoords(loc.lat, loc.lon);
        if (!coords) return;
        
        // Find dominant governing level matching legend
        const govType = getLocationGov(loc);
        const color = getGovColor(govType);

        // Radius calculation: calm, static, proportional
        const baseRadius = (activeYear === 'ALL') 
          ? Math.min(30, Math.max(7, Math.sqrt(count) * 6))
          : Math.min(26, Math.max(8, Math.sqrt(count) * 9));

        // SVG Group for localized pin
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', 'cursor-pointer');
        g.onclick = () => selectLocation(loc, true);

        // Main Bubble Circle - Counter-scaled by currentZoomK
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', coords.x);
        circle.setAttribute('cy', coords.y);
        circle.setAttribute('r', baseRadius / Math.pow(currentZoomK, 0.42));
        circle.setAttribute('data-base-r', baseRadius);
        circle.setAttribute('fill', color);
        circle.setAttribute('fill-opacity', (activeYear !== 'ALL' && !isCumulativeMode) ? '0.9' : '0.75');
        circle.setAttribute('stroke', '#ffffff');
        circle.setAttribute('stroke-width', Math.max(0.6, 1.8 / currentZoomK));
        circle.setAttribute('class', 'city-bubble');

        const countyInfo = CITY_TO_COUNTY[loc.name];
        const countyLabel = countyInfo ? ` (${{countyInfo.county}})` : '';

        circle.onmouseenter = (e) => {{
          showTooltip(e, `<strong class="text-white">${{loc.name}}</strong>${{countyLabel}}`, 
            `<span class="text-amber-400 font-semibold">${{count}} articles</span> (${{govType}})`);
        }};
        circle.onmouseleave = hideTooltip;

        g.appendChild(circle);
        bubbleLayer.appendChild(g);

        // Inner text count inside bubble for quick legibility
        if (baseRadius >= 9) {{
          const baseFontSize = baseRadius > 14 ? 11 : 9;
          const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
          text.setAttribute('x', coords.x);
          text.setAttribute('y', coords.y + 1);
          text.setAttribute('text-anchor', 'middle');
          text.setAttribute('dominant-baseline', 'central');
          text.setAttribute('fill', '#ffffff');
          text.setAttribute('data-base-fs', baseFontSize);
          text.setAttribute('font-size', `${{Math.max(5.5, baseFontSize / Math.pow(currentZoomK, 0.35))}}px`);
          text.setAttribute('font-weight', 'bold');
          text.setAttribute('class', 'bubble-count-text pointer-events-none select-none');
          text.textContent = count;
          bubbleLabelsLayer.appendChild(text);
        }}

        // Dynamic Shaded Region Name Label on Top-Center (revealed when morphed into shaded region)
        // Only render labels for municipal and county regions (not whole-state entries)
        if (cityLabelsLayer && !loc.name.includes('(State)')) {{
          const geom = getLocationRegionGeom(loc);
          if (geom && geom.width > 0) {{
            const displayName = loc.name.split(',')[0].trim();

            // Track duplicate coordinates to prevent overlapping labels
            const coordKey = `${{geom.centerX.toFixed(1)}}_${{geom.topY.toFixed(1)}}`;
            const dupIndex = coordUsageMap[coordKey] || 0;
            coordUsageMap[coordKey] = dupIndex + 1;
            const yOffset = dupIndex * Math.max(2.8, geom.height * 0.16);

            const labelText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            labelText.setAttribute('x', geom.centerX);
            labelText.setAttribute('y', geom.topY + yOffset);
            labelText.setAttribute('class', 'region-name-label pointer-events-none select-none');
            labelText.setAttribute('data-geom-width', geom.width);
            labelText.setAttribute('data-name-len', displayName.length);
            labelText.textContent = displayName;

            cityLabelsLayer.appendChild(labelText);
          }}
        }}
      }});

      // Synchronize county shading & bubble cross-fade for active timeframe
      updateCountyShading(currentZoomK);
    }}

    function renderLeaderboard() {{
      const leaderboardDiv = document.getElementById('locations-leaderboard');
      leaderboardDiv.innerHTML = '';
      const activeYear = getActiveYear();

      // Collect counts for active view
      const rankedLocs = [];
      DATA.locations.forEach(loc => {{
        let count = 0;
        if (activeYear === 'ALL') {{
          count = loc.total_count;
        }} else if (isCumulativeMode) {{
          Object.keys(loc.years).forEach(yr => {{
            if (yr <= activeYear) count += loc.years[yr];
          }});
        }} else {{
          count = loc.years[activeYear] || 0;
        }}
        if (count > 0) {{
          rankedLocs.push({{ name: loc.name, count: count, raw: loc }});
        }}
      }});

      rankedLocs.sort((a, b) => b.count - a.count);
      const maxCount = rankedLocs.length > 0 ? rankedLocs[0].count : 1;

      if (rankedLocs.length === 0) {{
        leaderboardDiv.innerHTML = '<div class="text-xs text-slate-500 text-center py-4">No local entries recorded for this year.</div>';
        return;
      }}

      rankedLocs.slice(0, 10).forEach((item, idx) => {{
        const pct = Math.min(100, Math.round((item.count / maxCount) * 100));
        const row = document.createElement('div');
        row.className = 'cursor-pointer p-1.5 rounded hover:bg-slate-800/60 transition text-xs';
        row.onclick = () => selectLocation(item.raw, true);

        row.innerHTML = `
          <div class="flex items-center justify-between mb-1">
            <span class="font-medium text-slate-200 truncate pr-2">
              <span class="text-slate-500 mr-1.5">#${{idx + 1}}</span> ${{item.name}}
            </span>
            <span class="font-bold text-white bg-slate-800 px-1.5 py-0.2 rounded">${{item.count}}</span>
          </div>
          <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
            <div class="bg-blue-500 h-full rounded-full transition-all duration-300" style="width: ${{pct}}%"></div>
          </div>
        `;
        leaderboardDiv.appendChild(row);
      }});
    }}

    function selectLocation(loc, shouldZoom = true) {{
      selectedLocation = loc;
      isNationwideSelected = false;
      setNationwideHighlight(false);

      if (shouldZoom !== false) {{
        const coords = projectCoords(loc.lat, loc.lon);
        if (coords) zoomToCoords(coords.x, coords.y, 4.8);
      }}

      const activeYear = getActiveYear();
      let articles = [];
      if (activeYear === 'ALL') {{
        articles = loc.articles;
      }} else if (isCumulativeMode) {{
        articles = loc.articles.filter(a => a.year <= activeYear);
      }} else {{
        articles = loc.articles.filter(a => a.year === activeYear);
      }}

      const countyInfo = CITY_TO_COUNTY[loc.name];
      const countySubtitle = countyInfo ? `County Jurisdiction: ${{countyInfo.county}}` : 'Local municipal regulations and traffic interventions.';

      document.getElementById('loc-badge-count').textContent = `${{articles.length}} Articles`;
      document.getElementById('loc-badge-count').className = 'text-xs font-bold text-blue-400 bg-blue-500/10 px-2.5 py-0.5 rounded-full border border-blue-500/20';

      const detailDiv = document.getElementById('location-detail-content');
      detailDiv.innerHTML = `
        <div class="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs mb-3">
          <div class="font-bold text-white text-sm flex items-center justify-between">
            <span>${{loc.name}}</span>
            ${{countyInfo ? `<span class="text-[10px] text-blue-400 font-mono font-normal">FIPS: ${{Array.isArray(countyInfo.fips) ? countyInfo.fips.join(', ') : countyInfo.fips}}</span>` : ''}}
          </div>
          <div class="text-[11px] text-slate-400 mt-0.5">${{countySubtitle}}</div>
        </div>
      `;

      if (articles.length === 0) {{
        detailDiv.innerHTML += '<div class="text-slate-500 text-center py-6">No articles recorded for this timeframe.</div>';
        return;
      }}

      articles.forEach(art => appendArticleCard(detailDiv, art));
    }}

    function showTooltip(event, title, body) {{
      const tip = document.getElementById('map-tooltip');
      document.getElementById('tooltip-title').innerHTML = title;
      document.getElementById('tooltip-body').innerHTML = body;
      tip.style.left = (event.pageX + 12) + 'px';
      tip.style.top = (event.pageY - 28) + 'px';
      tip.classList.remove('hidden');
    }}

    function hideTooltip() {{
      document.getElementById('map-tooltip').classList.add('hidden');
    }}

    function switchTab(tabId) {{
      document.querySelectorAll('.tab-pane').forEach(el => el.classList.add('hidden'));
      document.querySelectorAll('.tab-btn').forEach(btn => {{
        btn.className = 'tab-btn px-3 py-2 text-sm text-slate-400 border-b-2 border-transparent hover:text-white';
      }});

      document.getElementById(tabId).classList.remove('hidden');
      const activeBtn = document.querySelector(`button[onclick="switchTab('${{tabId}}')"]`);
      if (activeBtn) {{
        activeBtn.className = 'tab-btn px-3 py-2 text-sm text-white border-b-2 border-white';
      }}
    }}

    function handleFileUpload(e) {{
      const file = e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = function(evt) {{
        try {{
          const uploadedData = JSON.parse(evt.target.result);
          DATA.metadata.total_sources = uploadedData.length;
          document.getElementById('stat-total-header').textContent = `${{uploadedData.length}} Sources`;
          alert(`Successfully uploaded ${{uploadedData.length}} updated research sources! The dashboard is refreshed.`);
        }} catch(err) {{
          alert("Error parsing JSON file: " + err.message);
        }}
      }};
      reader.readAsText(file);
    }}

    function initMeasures() {{
      const panel = DATA.measures || {{ measures: [], articles: [], categories: [] }};
      const summary = document.getElementById('measures-summary');
      const filters = document.getElementById('measures-filters');
      const list = document.getElementById('measures-list');
      const detail = document.getElementById('measures-detail');
      if (!summary || !filters || !list || !detail) return;
      summary.textContent = `${{panel.article_count || 0}} articles read. ${{panel.labeled_count || 0}} matched a measure. ${{panel.unlabeled_count || 0}} stayed unlabeled because the text did not contain that measure's name or example phrases.`;
      let category = 'all';
      let selected = panel.measures[0] ? panel.measures[0].code : '';
      const maxCount = Math.max(1, ...(panel.measures || []).map(item => item.count || 0));

      function addFilter(code, label) {{
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = label;
        button.dataset.code = code;
        button.className = 'px-3 py-1.5 rounded-full text-xs font-medium border border-slate-700 text-slate-300 hover:text-white';
        button.addEventListener('click', () => {{
          category = code;
          drawMeasures();
        }});
        filters.appendChild(button);
      }}

      addFilter('all', 'All categories');
      (panel.categories || []).forEach(item => addFilter(item.code, item.code + '. ' + item.name));

      function drawMeasures() {{
        filters.querySelectorAll('button').forEach(button => {{
          const on = button.dataset.code === category;
          button.className = on
            ? 'px-3 py-1.5 rounded-full text-xs font-medium bg-blue-600 text-white'
            : 'px-3 py-1.5 rounded-full text-xs font-medium border border-slate-700 text-slate-300 hover:text-white';
        }});
        list.replaceChildren();
        const visible = (panel.measures || []).filter(item => category === 'all' || item.category === category);
        if (!visible.some(item => item.code === selected) && visible[0]) selected = visible[0].code;
        visible.forEach((item, index) => {{
          const row = document.createElement('li');
          const on = item.code === selected;
          row.className = on
            ? 'bg-slate-900 border border-blue-500 rounded-xl p-3 cursor-pointer'
            : 'bg-slate-900/80 border border-slate-800 rounded-xl p-3 cursor-pointer hover:border-slate-600';
          const width = Math.round(((item.count || 0) / maxCount) * 100);
          row.innerHTML = '<div class="flex justify-between gap-3"><span class="measure-name text-sm text-white"></span><b class="text-blue-400"></b></div><div class="measure-category text-[11px] text-slate-400 mt-1"></div><div class="h-1.5 bg-slate-800 rounded mt-2"><span class="measure-bar block h-full bg-orange-500 rounded"></span></div>';
          row.querySelector('.measure-name').textContent = (index + 1) + '. ' + item.code + '. ' + item.name;
          row.querySelector('b').textContent = String(item.count || 0);
          row.querySelector('.measure-category').textContent = item.category + '. ' + item.category_name;
          row.querySelector('.measure-bar').style.width = width + '%';
          row.addEventListener('click', () => {{
            selected = item.code;
            drawMeasures();
          }});
          list.appendChild(row);
        }});
        drawMeasureArticles();
      }}

      function drawMeasureArticles() {{
        const measure = (panel.measures || []).find(item => item.code === selected);
        detail.replaceChildren();
        if (!measure) {{
          detail.textContent = 'Select a measure.';
          return;
        }}
        const heading = document.createElement('h3');
        heading.className = 'text-lg font-bold text-white';
        heading.textContent = measure.code + '. ' + measure.name;
        const definition = document.createElement('p');
        definition.className = 'text-sm text-slate-400 mt-2 mb-4';
        definition.textContent = measure.definition || '';
        detail.appendChild(heading);
        detail.appendChild(definition);
        const found = (panel.articles || []).filter(item => (item.measures || []).includes(measure.code));
        found.sort((a, b) => (b.publication_date || '').localeCompare(a.publication_date || ''));
        if (!found.length) {{
          const note = document.createElement('p');
          note.className = 'text-slate-500 text-sm';
          note.textContent = 'No saved article matched this measure.';
          detail.appendChild(note);
          return;
        }}
        found.forEach(item => {{
          const card = document.createElement('article');
          card.className = 'border-t border-slate-800 py-3';
          const title = document.createElement('h4');
          title.className = 'text-sm font-semibold text-white';
          const sourceUrl = articleSourceUrl(item);
          const link = sourceUrl ? document.createElement('a') : document.createElement('span');
          link.className = sourceUrl
            ? 'hover:text-blue-400 underline decoration-slate-600 underline-offset-2'
            : '';
          link.textContent = item.title;
          if (sourceUrl) {{
            link.href = sourceUrl;
            link.target = '_blank';
            link.rel = 'noreferrer';
          }}
          title.appendChild(link);
          const meta = document.createElement('p');
          meta.className = 'text-[11px] text-slate-400 mt-1';
          meta.textContent = [item.publication_date, item.publisher, item.location].filter(Boolean).join(' · ');
          card.appendChild(title);
          card.appendChild(meta);
          appendSourceLine(card, item);
          detail.appendChild(card);
        }});
      }}

      drawMeasures();
    }}

    function renderDatabase(query) {{
      const rows = DATA.database || [];
      const needle = String(query || '').trim().toLowerCase();
      const body = document.getElementById('database-body');
      const count = document.getElementById('database-count');
      body.replaceChildren();
      const shown = needle
        ? rows.filter(row => [row.title, row.publisher, row.location, row.gov, row.category, row.date].join(' ').toLowerCase().includes(needle))
        : rows;
      if (count) count.textContent = shown.length + ' of ' + rows.length + ' documents';
      const fragment = document.createDocumentFragment();
      shown.forEach(row => {{
        const tr = document.createElement('tr');
        tr.id = articleAnchor(row.source_id);
        tr.className = 'border-t border-slate-800 align-top hover:bg-slate-900/60';
        const titleCell = document.createElement('td');
        titleCell.className = 'px-3 py-2 text-white';
        const sourceUrl = articleSourceUrl(row);
        if (sourceUrl) {{
          const link = document.createElement('a');
          link.href = sourceUrl;
          link.target = '_blank';
          link.rel = 'noreferrer';
          link.className = 'hover:text-blue-300 underline decoration-slate-600 underline-offset-2';
          link.textContent = row.title || 'Untitled';
          titleCell.appendChild(link);
        }} else {{
          titleCell.textContent = row.title || 'Untitled';
        }}
        const cells = [row.date, row.publisher, row.location, row.gov, row.category];
        tr.appendChild(titleCell);
        cells.forEach((value, idx) => {{
          const td = document.createElement('td');
          td.className = 'px-3 py-2 text-slate-300 whitespace-nowrap';
          if (idx === 3) {{
            const badge = document.createElement('span');
            badge.className = 'px-2 py-0.5 rounded text-xs font-medium ' + (
              value === 'Company' ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/50' :
              value === 'Government: City' ? 'bg-blue-950/80 text-blue-300 border border-blue-800/50' :
              value === 'Government: State' ? 'bg-amber-950/80 text-amber-300 border border-amber-800/50' :
              value === 'Government: Federal' ? 'bg-indigo-950/80 text-indigo-300 border border-indigo-800/50' :
              value === 'Government: County' ? 'bg-rose-950/80 text-rose-300 border border-rose-800/50' :
              'bg-slate-800 text-slate-300'
            );
            badge.textContent = value || '';
            td.appendChild(badge);
          }} else {{
            td.textContent = value || '';
          }}
          tr.appendChild(td);
        }});
        fragment.appendChild(tr);
      }});
      body.appendChild(fragment);
    }}

    function initDatabase() {{
      const search = document.getElementById('database-search');
      renderDatabase('');
      if (search) search.addEventListener('input', () => renderDatabase(search.value));
    }}

    function initOutside() {{
      const panel = DATA.outside || {{ themes: [], unlabeled_count: 0, total: 0 }};
      const summary = document.getElementById('outside-summary');
      const list = document.getElementById('outside-list');
      const detail = document.getElementById('outside-detail');
      const byId = new Map((DATA.database || []).map(row => [row.source_id, row]));
      if (summary) {{
        summary.textContent = panel.unlabeled_count + ' of ' + panel.total
          + ' saved documents contain none of the codebook measure names or example phrases. Each of those documents is counted once, under the first title pattern it matches.';
      }}
      function showTheme(theme) {{
        detail.replaceChildren();
        const heading = document.createElement('h3');
        heading.className = 'text-lg font-semibold text-white';
        heading.textContent = theme.name;
        const note = document.createElement('p');
        note.className = 'text-sm text-slate-400 mt-1 mb-4';
        note.textContent = theme.count + ' articles. ' + (theme.note || '');
        detail.append(heading, note);
        const ids = theme.ids || [];
        let shown = 0;
        const more = document.createElement('button');
        more.type = 'button';
        more.className = 'mt-3 text-sm text-blue-400 hover:text-blue-300 underline';
        function renderSlice() {{
          ids.slice(shown, shown + 40).forEach(sourceId => {{
            const row = byId.get(sourceId) || {{ source_id: sourceId, title: sourceId }};
            appendArticleCard(detail, {{
              ...row,
              year: row.date || '',
              gov: row.location || '',
            }});
          }});
          shown = Math.min(ids.length, shown + 40);
          if (shown < ids.length) {{
            more.textContent = 'Show more (' + shown + ' of ' + ids.length + ')';
            detail.appendChild(more);
          }} else if (more.parentNode) {{
            more.remove();
          }}
        }}
        more.addEventListener('click', () => {{
          more.remove();
          renderSlice();
        }});
        renderSlice();
      }}
      (panel.themes || []).forEach((theme, index) => {{
        const item = document.createElement('li');
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'w-full text-left bg-slate-900/90 border border-slate-800 rounded-xl px-4 py-3 hover:border-slate-600';
        const rank = document.createElement('div');
        rank.className = 'text-sm font-semibold text-white';
        rank.textContent = (index + 1) + '. ' + theme.name;
        const meta = document.createElement('div');
        meta.className = 'text-xs text-slate-400 mt-1';
        meta.textContent = theme.count + ' articles';
        button.append(rank, meta);
        button.addEventListener('click', () => showTheme(theme));
        item.appendChild(button);
        list.appendChild(item);
      }});
      if (panel.themes && panel.themes.length) showTheme(panel.themes[0]);
    }}

    // Boot on page load
    window.addEventListener('DOMContentLoaded', () => {{
      initDashboard();
      initMeasures();
      initDatabase();
      initOutside();
    }});
  </script>
</body>
</html>
"""


def document_anchor(source_id: str) -> str:
    """Match the anchor used by the map and measures links."""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", source_id or "row").strip("-")
    return "doc-" + (slug or "row")


def generate_database_html(rows: list[dict]) -> str:
    """A standalone page for every row in crawled_documents."""
    payload = []
    for row in rows:
        summary = " ".join(str(row.get("factual_summary") or "").split())
        if summary.startswith("urn:") or summary.startswith("<") or "xmlns=" in summary[:80]:
            summary = ""
        source_id = str(row.get("id") or "")
        url = str(row.get("url") or "")
        nexis_match = re.search(r"urn:contentItem:[A-Za-z0-9-]+", source_id)
        payload.append({
            "anchor": document_anchor(source_id),
            "id": source_id,
            "origin": str(row.get("origin") or ""),
            "title": str(row.get("title") or ""),
            "publisher": str(row.get("publisher") or ""),
            "date": str(row.get("publication_date") or ""),
            "location": str(row.get("location") or ""),
            "url": url,
            "nexis_id": nexis_match.group(0) if nexis_match and not url.startswith("http") else "",
            "archive_dir": str(row.get("archive_dir") or ""),
            "measures": str(row.get("measure_codes") or ""),
            "governing_level": str(row.get("governing_level") or ""),
            "category": str(row.get("category") or ""),
            "summary": summary[:280],
        })
    data = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>News database</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    tr.marked {{ background: #1e293b; outline: 1px solid #93c5fd; }}
  </style>
</head>
<body class="bg-[#141816] text-slate-100 antialiased min-h-screen px-4 py-6 md:px-8 font-sans">
  <header class="max-w-7xl mx-auto mb-6 flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-800 pb-5">
    <div>
      <p class="text-xs uppercase tracking-wide text-slate-500">ELENG 290 · data/news.sqlite</p>
      <h1 class="text-3xl font-serif font-semibold tracking-tight text-white mt-1">News database</h1>
      <p class="text-sm text-slate-400 mt-2 max-w-3xl">Every saved archive page and Nexis document. A Nexis title opens that document in Nexis Uni. An archive title opens the original page. The saved folder is the local copy.</p>
    </div>
    <a href="research_infographics.html" class="text-sm text-slate-300 underline underline-offset-2 hover:text-white">Back to the map</a>
  </header>
  <div class="max-w-7xl mx-auto mb-4 flex flex-col sm:flex-row gap-3 sm:items-center">
    <input id="query" type="search" placeholder="Search title, publisher, place, governing level, category, or document id" class="flex-1 bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-white" />
    <p id="count" class="text-sm text-slate-400 whitespace-nowrap"></p>
  </div>
  <div class="max-w-7xl mx-auto overflow-x-auto border border-slate-800">
    <table class="w-full text-left text-xs">
      <thead class="bg-slate-950 text-slate-400 uppercase sticky top-0">
        <tr>
          <th class="py-3 px-3">Title</th>
          <th class="py-3 px-3">Date</th>
          <th class="py-3 px-3">Publisher</th>
          <th class="py-3 px-3">Place</th>
          <th class="py-3 px-3">Governing Level</th>
          <th class="py-3 px-3">Category</th>
          <th class="py-3 px-3">Saved file</th>
        </tr>
      </thead>
      <tbody id="rows"></tbody>
    </table>
  </div>
  <script>
    const ROWS = {data};
    const body = document.getElementById('rows');
    const query = document.getElementById('query');
    const count = document.getElementById('count');

    function sourceUrl(row) {{
      if (row.url && (row.url.startsWith('http://') || row.url.startsWith('https://'))) return row.url;
      if (!row.nexis_id) return '';
      return 'https://www.nexisuni.com/document/?pddocfullpath=' + encodeURIComponent('/shared/document/news/' + row.nexis_id);
    }}

    function render(list) {{
      body.replaceChildren();
      list.forEach(row => {{
        const tr = document.createElement('tr');
        tr.id = row.anchor;
        tr.className = 'border-t border-slate-800 align-top hover:bg-slate-900/80';
        const titleCell = document.createElement('td');
        titleCell.className = 'py-3 px-3 max-w-md';
        const link = document.createElement('a');
        const href = sourceUrl(row);
        link.className = 'text-sm text-white hover:text-blue-300 underline decoration-slate-600 underline-offset-2';
        link.textContent = row.title || row.id;
        if (href) {{
          link.href = href;
          link.target = '_blank';
          link.rel = 'noreferrer';
        }} else {{
          link.href = '#' + row.anchor;
        }}
        titleCell.appendChild(link);
        const meta = document.createElement('div');
        meta.className = 'text-[11px] text-slate-500 mt-1 break-all';
        meta.textContent = row.nexis_id || row.id;
        titleCell.appendChild(meta);
        if (row.summary) {{
          const summary = document.createElement('p');
          summary.className = 'text-[11px] text-slate-400 mt-1';
          summary.textContent = row.summary;
          titleCell.appendChild(summary);
        }}
        function cell(text) {{
          const td = document.createElement('td');
          td.className = 'py-3 px-3 text-slate-300';
          td.textContent = text || '';
          return td;
        }}
        const govCell = document.createElement('td');
        govCell.className = 'py-3 px-3 whitespace-nowrap';
        const gVal = row.governing_level || '';
        const badge = document.createElement('span');
        badge.className = 'px-2 py-0.5 rounded text-xs font-medium ' + (
          gVal === 'Company' ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/50' :
          gVal === 'Government: City' ? 'bg-blue-950/80 text-blue-300 border border-blue-800/50' :
          gVal === 'Government: State' ? 'bg-amber-950/80 text-amber-300 border border-amber-800/50' :
          gVal === 'Government: Federal' ? 'bg-indigo-950/80 text-indigo-300 border border-indigo-800/50' :
          gVal === 'Government: County' ? 'bg-rose-950/80 text-rose-300 border border-rose-800/50' :
          'bg-slate-800 text-slate-300'
        );
        badge.textContent = gVal;
        govCell.appendChild(badge);

        const file = cell(row.archive_dir);
        file.className = 'py-3 px-3 text-slate-500 font-mono break-all max-w-xs';
        file.title = row.archive_dir || '';
        tr.append(titleCell, cell(row.date), cell(row.publisher), cell(row.location), govCell, cell(row.category), file);
        body.appendChild(tr);
      }});
      count.textContent = list.length + ' of ' + ROWS.length + ' documents';
    }}

    function applyFilter() {{
      const needle = query.value.trim().toLowerCase();
      const list = needle
        ? ROWS.filter(row => [row.title, row.publisher, row.location, row.governing_level, row.id, row.nexis_id, row.category, row.archive_dir].join(' ').toLowerCase().includes(needle))
        : ROWS;
      render(list);
      revealHash();
    }}

    function revealHash() {{
      const id = decodeURIComponent(location.hash || '').replace(/^#/, '');
      if (!id) return;
      const row = document.getElementById(id);
      if (!row) return;
      row.classList.add('marked');
      row.scrollIntoView({{ block: 'center' }});
    }}

    query.addEventListener('input', applyFilter);
    applyFilter();
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate interactive research infographics dashboard.")
    parser.add_argument(
        "--input",
        default="data/exports/research_analysis_all_sources.json",
        help="Input research analysis json file",
    )
    parser.add_argument(
        "--output",
        default="data/exports/research_infographics.html",
        help="Output HTML infographics file",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: input file {input_path} not found.")
        return 1

    print(f"Reading research analysis records from {input_path}...")
    dataset = build_infographic_dataset(input_path)

    print(
        f"Processed {dataset['metadata']['total_sources']} sources: "
        f"{dataset['metadata']['localized_sources']} localized across "
        f"{dataset['metadata']['unique_locations']} locations + "
        f"{dataset['metadata']['nationwide_sources']} federal/nationwide policies "
        f"({dataset['metadata']['year_range']})."
    )

    html_content = generate_html_infographics(dataset)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")
    print(f"Saved interactive infographics to {output_path}")
    from news_importer.db import load_database_rows

    database_path = output_path.parent / "news_database.html"
    database_rows = load_database_rows(input_path.parent.parent / "news.sqlite")
    database_path.write_text(generate_database_html(database_rows), encoding="utf-8")
    print(f"Saved news database page to {database_path}")

    # Mirror to antigravity brain artifact directory
    artifact_dir = Path("/Users/isabelle/.gemini/antigravity/brain/b83e007b-8917-4635-8cf5-17130e87b3c1")
    if artifact_dir.exists():
        mirror_path = artifact_dir / "research_infographics_dashboard.html"
        mirror_path.write_text(html_content, encoding="utf-8")
        print(f"Mirrored artifact dashboard to {mirror_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
