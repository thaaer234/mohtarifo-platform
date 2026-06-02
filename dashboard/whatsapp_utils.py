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

def send_whatsapp_message(phone_number, message_text, raw_text=None):
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
            
            # Log sent message and its raw hash to avoid duplicates
            try:
                from dashboard.models import WhatsAppMessageLog
                import hashlib
                text_to_hash = raw_text or message_text
                normalized = " ".join(text_to_hash.strip().split()) if text_to_hash else ""
                raw_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest() if normalized else ""
                
                WhatsAppMessageLog.objects.create(
                    phone=formatted_number,
                    raw_text_hash=raw_hash,
                    sent_text=message_text
                )
            except Exception as log_err:
                logger.error(f"Failed to log WhatsApp message to database: {log_err}")
                
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

def guess_gender_from_name(full_name):
    """
    Analyzes Levant/Syrian first names to heuristically predict student gender.
    """
    if not full_name:
        return 'unknown'
    
    parts = full_name.strip().split()
    if not parts:
        return 'unknown'
        
    # Normalize string, replacing specific Syrian variants
    first_name = parts[0].replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')
    
    # Top Levant Syrian female names
    female_names = {
        "شام", "حلا", "لين", "رهف", "رغد", "شهد", "غلا", "نور", "مريم", "رؤى", "ريم", "تسنيم", "فاطمه",
        "بتول", "تالا", "ماسه", "مياس", "جودي", "مرح", "جنى", "ريتاج", "فرح", "روان", "علا", "غنى", "سيدرا", 
        "سدره", "هبه", "منى", "ياسمين", "راما", "رشا", "مرام", "رند", "نادين", "لارا", "هديل", "ولاء", "لميس",
        "نورال", "سلام", "اريج", "وئام", "بيان", "شيرين", "خلود", "شروق", "سجى", "سحر", "سما", "رنا", "هاله",
        "مي", "ميرنا", "لجين", "جيهان", "غدير", "عبير", "عبير", "فاتن", "ناديا", "نجوى", "نهى", "شوق"
    }
    
    if first_name in female_names:
        return 'female'
        
    # Common male exceptions ending in feminine vowels
    male_exceptions = {
        "علاء", "بهاء", "ضياء", "حمزه", "عبيده", "قتيبه", "طلحه", "اسامه", "حذيفه", "عروه", "زكريا", 
        "يحيى", "مصطفى", "موسى", "عيسى", "طه", "رضا", "مرتضى"
    }
    if first_name in male_exceptions:
        return 'male'
        
    # General phonological patterns
    if first_name.endswith('ه'):  # normalized 'ة'
        return 'female'
    if first_name.endswith('ى'):
        return 'female'
    if first_name.endswith('اء') and not first_name.endswith('لاء') and not first_name.endswith('هاء'):
        return 'female'
        
    return 'male'

def parse_gender_grammar(text, gender):
    """
    Parses syntax like {مذكر|مؤنث} dynamically based on target gender.
    E.g. "أهلاً {يا بطل|يا بطلة}" becomes "أهلاً يا بطل" for male/unknown, or "أهلاً يا بطلة" for female.
    """
    import re
    if not text:
        return ""
        
    # Find all occurrences of {something | something}
    matches = re.findall(r'\{([^|]+)\|([^}]+)\}', text)
    for opt_male, opt_female in matches:
        original_token = "{" + opt_male + "|" + opt_female + "}"
        if gender == 'female':
            text = text.replace(original_token, opt_female.strip())
        else:
            # Defaults to male for unknown or male
            text = text.replace(original_token, opt_male.strip())
    return text
