"""
OTP (One-Time Password) service for WhatsApp-based authentication.
Handles OTP generation, storage, validation, and WhatsApp delivery.
"""
import random
import logging
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.models import User

from .whatsapp_utils import send_whatsapp_message, format_phone_to_intl
from .models import OTPVerificationLog

logger = logging.getLogger(__name__)

# Configuration
OTP_LENGTH = 6
OTP_EXPIRY_SECONDS = 300  # 5 minutes
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60  # 1 minute between resends
OTP_MAX_DAILY_SENDS = 10  # Max OTPs per phone per day


def _otp_cache_key(phone, purpose="auth"):
    """Generate a unique cache key for OTP storage."""
    return f"otp:{purpose}:{phone}"


def _otp_attempts_key(phone, purpose="auth"):
    """Generate a unique cache key for tracking verification attempts."""
    return f"otp_attempts:{purpose}:{phone}"


def _otp_resend_key(phone, purpose="auth"):
    """Generate a cache key for resend cooldown."""
    return f"otp_resend:{purpose}:{phone}"


def _otp_daily_key(phone):
    """Generate a cache key for daily send limit."""
    today = timezone.now().strftime("%Y-%m-%d")
    return f"otp_daily:{phone}:{today}"


def generate_otp():
    """Generate a random N-digit OTP code."""
    return ''.join([str(random.randint(0, 9)) for _ in range(OTP_LENGTH)])


def send_otp(phone, purpose="register", request=None):
    """
    Generate and send an OTP to the given phone number via WhatsApp.
    
    Args:
        phone: The phone number (raw format, e.g. 0912345678)
        purpose: Either 'register', 'login', or 'reset_password'
        request: The Django request object (optional, for IP tracking)
    
    Returns:
        dict with keys: success (bool), message (str), cooldown_remaining (int, optional)
    """
    # Check resend cooldown
    resend_key = _otp_resend_key(phone, purpose)
    cooldown_ttl = cache.ttl(resend_key) if hasattr(cache, 'ttl') else None
    
    if cache.get(resend_key):
        remaining = cooldown_ttl if cooldown_ttl and cooldown_ttl > 0 else OTP_RESEND_COOLDOWN_SECONDS
        return {
            "success": False,
            "message": f"الرجاء الانتظار قبل إعادة إرسال الرمز.",
            "cooldown_remaining": remaining,
        }
    
    # Check daily limit
    daily_key = _otp_daily_key(phone)
    daily_count = int(cache.get(daily_key, 0))
    if daily_count >= OTP_MAX_DAILY_SENDS:
        return {
            "success": False,
            "message": "تم تجاوز الحد الأقصى لإرسال رموز التحقق اليوم. حاول غداً.",
        }
    
    # Generate and store OTP
    otp_code = generate_otp()
    cache_key = _otp_cache_key(phone, purpose)
    cache.set(cache_key, otp_code, OTP_EXPIRY_SECONDS)
    
    # Track in Database Log
    ip = None
    if request:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.META.get("REMOTE_ADDR")
    
    user = None
    if purpose != "register":
        user = User.objects.filter(username=phone).first()

    OTPVerificationLog.objects.create(
        phone=phone,
        user=user,
        code=otp_code,
        purpose=purpose,
        ip_address=ip
    )
    
    # Reset verification attempts
    attempts_key = _otp_attempts_key(phone, purpose)
    cache.delete(attempts_key)
    
    # Set resend cooldown
    cache.set(resend_key, True, OTP_RESEND_COOLDOWN_SECONDS)
    
    # Increment daily counter
    try:
        cache.incr(daily_key)
    except ValueError:
        cache.set(daily_key, 1, 86400)  # 24 hours
    
    # Build WhatsApp message
    if purpose == "register":
        message = (
            f"🔐 رمز التحقق لإنشاء حسابك في محترفو التعليم:\n\n"
            f"✨ الرمز: *{otp_code}*\n\n"
            f"⏰ صالح لمدة {OTP_EXPIRY_SECONDS // 60} دقائق فقط.\n"
            f"⚠️ لا تشارك هذا الرمز مع أي شخص."
        )
    elif purpose == "reset_password":
        message = (
            f"🛠️ رمز استعادة كلمة المرور في محترفو التعليم:\n\n"
            f"✨ الرمز: *{otp_code}*\n\n"
            f"⏰ صالح لمدة {OTP_EXPIRY_SECONDS // 60} دقائق فقط.\n"
            f"⚠️ إذا لم تطلب هذا الرمز، يرجى تجاهل الرسالة."
        )
    else:
        message = (
            f"🔑 رمز تسجيل الدخول لحسابك في محترفو التعليم:\n\n"
            f"✨ الرمز: *{otp_code}*\n\n"
            f"⏰ صالح لمدة {OTP_EXPIRY_SECONDS // 60} دقائق فقط.\n"
            f"⚠️ لا تشارك هذا الرمز مع أي شخص."
        )
    
    # Send via WhatsApp (non-blocking would be better, but we need confirmation)
    sent = send_whatsapp_message(phone, message)
    
    if sent:
        logger.info(f"OTP sent to {phone} for {purpose}")
        return {
            "success": True,
            "message": "تم إرسال رمز التحقق إلى واتساب الخاص بك.",
        }
    else:
        # Clean up on failure
        cache.delete(cache_key)
        logger.error(f"Failed to send OTP to {phone} for {purpose}")
        return {
            "success": False,
            "message": "فشل إرسال رمز التحقق. تأكد من صحة الرقم أو حاول لاحقاً.",
        }


def verify_otp(phone, submitted_code, purpose="register"):
    """
    Verify an OTP code submitted by the user.
    
    Args:
        phone: The phone number
        submitted_code: The OTP code submitted by user
        purpose: Either 'register' or 'login'
    
    Returns:
        dict with keys: valid (bool), message (str)
    """
    if not submitted_code:
        return {"valid": False, "message": "الرجاء إدخال رمز التحقق."}
    
    # Check attempt limit
    attempts_key = _otp_attempts_key(phone, purpose)
    attempts = int(cache.get(attempts_key, 0))
    
    if attempts >= OTP_MAX_ATTEMPTS:
        # Invalidate OTP after too many attempts
        cache.delete(_otp_cache_key(phone, purpose))
        return {
            "valid": False,
            "message": "تم تجاوز عدد المحاولات المسموح. أعد إرسال رمز جديد.",
        }
    
    # Retrieve stored OTP
    cache_key = _otp_cache_key(phone, purpose)
    stored_otp = cache.get(cache_key)
    
    if not stored_otp:
        return {
            "valid": False,
            "message": "انتهت صلاحية رمز التحقق. أعد إرسال رمز جديد.",
        }
    
    # Verify
    submitted_code = str(submitted_code).strip()
    if submitted_code == str(stored_otp):
        # OTP is valid - clean up
        cache.delete(cache_key)
        cache.delete(attempts_key)
        
        # Mark as verified in Database
        OTPVerificationLog.objects.filter(
            phone=phone,
            code=submitted_code,
            purpose=purpose,
            is_verified=False
        ).update(is_verified=True, verified_at=timezone.now())
        
        logger.info(f"OTP verified for {phone} ({purpose})")
        return {"valid": True, "message": "تم التحقق بنجاح."}
    else:
        # Increment failed attempts
        try:
            cache.incr(attempts_key)
        except ValueError:
            cache.set(attempts_key, 1, OTP_EXPIRY_SECONDS)
        
        remaining = OTP_MAX_ATTEMPTS - attempts - 1
        return {
            "valid": False,
            "message": f"رمز التحقق غير صحيح. المحاولات المتبقية: {remaining}",
        }
