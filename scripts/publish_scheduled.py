#!/usr/bin/env python3
"""
Script to automatically publish scheduled content
This script should be run as a cron job every 5-10 minutes
"""

import requests
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/scheduled_content.log'),
        logging.StreamHandler()
    ]
)

def publish_scheduled_content():
    """Call the API endpoint to publish scheduled content"""
    try:
        # Get the backend URL from environment or use default
        backend_url = "http://localhost:8001"  # Internal backend URL
        
        response = requests.post(f"{backend_url}/api/content/publish-scheduled")
        
        if response.status_code == 200:
            result = response.json()
            logging.info(f"Successfully published scheduled content: {result['message']}")
            return True
        else:
            logging.error(f"Failed to publish scheduled content. Status: {response.status_code}, Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error when publishing scheduled content: {str(e)}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error when publishing scheduled content: {str(e)}")
        return False

if __name__ == "__main__":
    logging.info("Starting scheduled content publication job")
    
    success = publish_scheduled_content()
    
    if success:
        logging.info("Scheduled content publication completed successfully")
        sys.exit(0)
    else:
        logging.error("Scheduled content publication failed")
        sys.exit(1)