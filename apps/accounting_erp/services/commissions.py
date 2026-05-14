from decimal import Decimal
from ..models.rules import CommissionRule
from django.db.models import Q

class CommissionEngine:
    @staticmethod
    def calculate_split(amount, instructor=None, course=None, sales_center=None, academic_branch=None):
        """
        Calculates the financial split based on available rules.
        Amount should be a Decimal.
        """
        # Find the best matching active rule
        # Rules with higher priority and more specific matches are preferred
        query = Q(is_active=True)
        
        # Build specific matches
        specific_matches = []
        if instructor: specific_matches.append(Q(instructor=instructor))
        if course: specific_matches.append(Q(course=course))
        if sales_center: specific_matches.append(Q(sales_center=sales_center))
        if academic_branch: specific_matches.append(Q(academic_branch=academic_branch))
        
        # Try to find a rule that matches any of the provided parameters
        rule = CommissionRule.objects.filter(query).filter(
            Q(instructor=instructor) | Q(course=course) | Q(sales_center=sales_center) | Q(academic_branch=academic_branch) |
            Q(instructor__isnull=True, course__isnull=True, sales_center__isnull=True, academic_branch__isnull=True)
        ).first()

        # Fallback to default if no rule found
        if not rule:
            instructor_share = Decimal('0.40')
            platform_share = Decimal('0.45')
            center_share = Decimal('0.15')
        else:
            instructor_share = rule.instructor_share
            platform_share = rule.platform_share
            center_share = rule.center_share

        # Calculate absolute values
        return {
            'instructor_amount': (amount * instructor_share).quantize(Decimal('0.01')),
            'platform_amount': (amount * platform_share).quantize(Decimal('0.01')),
            'center_amount': (amount * center_share).quantize(Decimal('0.01')),
            'rule_applied': rule.name if rule else 'Default Fallback'
        }
