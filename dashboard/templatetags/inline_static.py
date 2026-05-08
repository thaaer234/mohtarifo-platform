import base64
import mimetypes

from django import template
from django.contrib.staticfiles import finders
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def inline_static(path):
    static_path = finders.find(path)
    if not static_path:
        return ''

    with open(static_path, encoding='utf-8') as static_file:
        return mark_safe(static_file.read())


@register.simple_tag
def static_data_uri(path):
    static_path = finders.find(path)
    if not static_path:
        return ''

    mime_type = mimetypes.guess_type(static_path)[0] or 'application/octet-stream'
    with open(static_path, 'rb') as static_file:
        encoded = base64.b64encode(static_file.read()).decode('ascii')

    return mark_safe(f'data:{mime_type};base64,{encoded}')


@register.simple_tag
def instructor_cover_static_path(instructor):
    instructor_name = (instructor.get_full_name() or instructor.username).strip()
    return f"dashboard/course-covers/{instructor_name}.png"


@register.filter
def currency_format(value):
    try:
        if value is None:
            return "0"
        val = float(value)
        if val.is_integer():
            return f"{int(val):,}"
        return f"{val:,.2f}"
    except (ValueError, TypeError):
        return value


@register.simple_tag
def course_discount_info(course_or_package):
    from billing.models import DiscountRule
    from django.utils import timezone
    from django.db.models import Q
    
    if not course_or_package or not course_or_package.price_cents:
        return {"has_discount": False, "original_price": 0, "discounted_price": 0, "discount_name": "", "discount_amount": 0}
        
    base_price_cents = course_or_package.price_cents
    original_price = base_price_cents / 100
    
    from learning.models import Course
    if isinstance(course_or_package, Course):
        target_track = course_or_package.academic_track
    else:
        target_track = getattr(course_or_package, "package_track", "all")
        
    now = timezone.now()
    rules = DiscountRule.objects.filter(
        is_active=True,
    ).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now),
        Q(expires_at__isnull=True) | Q(expires_at__gte=now)
    )
    if target_track != "all":
        if target_track == "general":
            rules = rules.filter(Q(academic_track="all") | Q(academic_track="general") | Q(academic_track="scientific") | Q(academic_track="literary"))
        else:
            rules = rules.filter(Q(academic_track="all") | Q(academic_track=target_track))
        
    best_rule = None
    max_discount_cents = 0
    
    for rule in rules:
        discount_cents = 0
        if rule.discount_percent > 0:
            discount_cents = (base_price_cents * rule.discount_percent) // 100
        elif rule.discount_amount_syp > 0:
            discount_cents = rule.discount_amount_syp * 100
            
        if discount_cents > max_discount_cents:
            max_discount_cents = min(discount_cents, base_price_cents)
            best_rule = rule
            
    if best_rule:
        discounted_price = (base_price_cents - max_discount_cents) / 100
        return {
            "has_discount": True,
            "original_price": original_price,
            "discounted_price": discounted_price,
            "discount_name": best_rule.name,
            "discount_amount": max_discount_cents / 100,
        }
        
    return {
        "has_discount": False,
        "original_price": original_price,
        "discounted_price": original_price,
        "discount_name": "",
        "discount_amount": 0,
    }


@register.simple_tag
def active_discount_for_popup(user):
    from billing.models import DiscountRule
    from django.utils import timezone
    from django.db.models import Q
    now = timezone.now()
    
    target_track = "all"
    if user and user.is_authenticated:
        profile = getattr(user, "student_profile", None)
        if profile:
            track_val = str(getattr(profile, "track", "") or "")
            if "علمي" in track_val or "scientific" in track_val:
                target_track = "scientific"
            elif "أدبي" in track_val or "literary" in track_val:
                target_track = "literary"
            elif "تاسع" in track_val or "ninth" in track_val:
                target_track = "ninth"
            elif "مشترك" in track_val or "general" in track_val:
                target_track = "general"
                
    rules = DiscountRule.objects.filter(is_active=True).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now),
        Q(expires_at__isnull=True) | Q(expires_at__gte=now)
    )
    if target_track != "all":
        specific_rule = rules.filter(academic_track=target_track).first()
        if specific_rule:
            return specific_rule
            
    all_rule = rules.filter(academic_track="all").first()
    if all_rule:
        return all_rule
    return rules.first()



