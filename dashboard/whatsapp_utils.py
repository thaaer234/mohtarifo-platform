import requests
import logging
import os

logger = logging.getLogger(__name__)

WHATSAPP_GATEWAY_URL = os.environ.get('WHATSAPP_GATEWAY_URL', 'http://127.0.0.1:3001')
WHATSAPP_API_SECRET = os.environ.get('WHATSAPP_API_SECRET', 'mohtarifo_internal_secret_123')

def format_phone_to_intl(phone):
    """Utility to normalize phone number for WhatsApp."""
    digits = ''.join(filter(str.isdigit, str(phone)))
    
    # Handle Syrian number logic (Standard in the region)
    # If number starts with 09 (10 digits) -> Convert to 9639...
    if len(digits) == 10 and digits.startswith('09'):
        return '963' + digits[1:]
    
    # If number starts with 9 without country code (9 digits)
    if len(digits) == 9 and digits.startswith('9'):
        return '963' + digits

    return digits

def send_whatsapp_message(phone_number, message_text):
    """
    Sends an automated WhatsApp message through the local microservice.
    Automatically catches exceptions to not interrupt the main application flow.
    """
    
    if not phone_number:
        logger.warning("Skipped WhatsApp: Phone number is empty.")
        return False
    
    formatted_number = format_phone_to_intl(phone_number)
    
    payload = {
        "number": formatted_number,
        "message": message_text
    }
    
    headers = {
        "X-API-Secret": WHATSAPP_API_SECRET,
        "Content-Type": "application/json"
    }
    
    try:
        endpoint = f"{WHATSAPP_GATEWAY_URL}/send-message"
        response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"WhatsApp sent successfully to {formatted_number}: {data.get('messageId')}")
            return True
        else:
            logger.error(f"Failed to send WhatsApp to {formatted_number}: HTTP {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to local WhatsApp Gateway: {e}")
        return False

def get_whatsapp_status():
    """Fetches node service status and QR code if disconnected."""
    headers = {"X-API-Secret": WHATSAPP_API_SECRET}
    try:
        resp = requests.get(f"{WHATSAPP_GATEWAY_URL}/status", headers=headers, timeout=3)
        return resp.json()
    except:
        return {"status": "offline"}

def logout_whatsapp():
    """Commands the node server to disconnect from WhatsApp."""
    headers = {"X-API-Secret": WHATSAPP_API_SECRET}
    try:
        resp = requests.post(f"{WHATSAPP_GATEWAY_URL}/logout", headers=headers, timeout=5)
        return resp.json()
    except:
        return {"status": "error"}
