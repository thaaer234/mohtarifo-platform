from decimal import Decimal
from django.db.models import Q
from ..models.rules import CommissionRule

class CommissionEngine:
    @staticmethod
    def calculate_shares(amount, instructor=None, course=None, sales_center=None, academic_branch=None):
        """
        Calculate shares for Instructor, Platform, and Center based on the best matching rule.
        """
        amount = Decimal(str(amount))
        
        # Build query for matching rules
        query = Q(is_active=True)
        filters = Q()
        
        if instructor:
            filters |= Q(instructor=instructor)
        if course:
            filters |= Q(course=course)
        if sales_center:
            filters |= Q(sales_center=sales_center)
        if academic_branch:
            filters |= Q(academic_branch=academic_branch)
            
        rule = CommissionRule.objects.filter(query & (filters | Q(instructor=None, course=None, sales_center=None, academic_branch=None))).first()
        
        if not rule:
            # Absolute fallback defaults
            instructor_pct = Decimal('0.4000')
            center_pct = Decimal('0.1500')
            platform_pct = Decimal('0.4500')
        else:
            instructor_pct = rule.instructor_share
            center_pct = rule.center_share
            platform_pct = rule.platform_share
            
        # Ensure they sum to 1.0 (or adjust platform)
        if (instructor_pct + center_pct + platform_pct) != Decimal('1.0000'):
            platform_pct = Decimal('1.0000') - instructor_pct - center_pct
            
        return {
            'instructor_amount': (amount * instructor_pct).quantize(Decimal('0.01')),
            'center_amount': (amount * center_pct).quantize(Decimal('0.01')),
            'platform_amount': (amount * platform_pct).quantize(Decimal('0.01')),
            'rule_name': rule.name if rule else 'Default Fallback'
        }
