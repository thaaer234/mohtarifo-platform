from decimal import Decimal
from django.db import transaction
from billing.models import CoursePurchase
from learning.models import Course
from ..models import RevenueShareAgreement, InstructorCommission

class CommissionProcessingService:
    """
    Handles calculation of instructor credit based on revenue share agreements.
    Called whenever new revenue enters the Financial Ledger.
    """
    
    @classmethod
    def process_ledger_entry(cls, ledger_entry):
        """
        Examines a ledger transaction and splits it across relevant stakeholders.
        """
        if ledger_entry.entry_type != 'revenue':
            return False
            
        # Check if this revenue links to a specific course purchase to find authors
        # We query based on the external logical ID captured during ETL
        try:
            # We retrieve by casting logically known mapping
            from billing.models import Payment
            if ledger_entry.external_source != 'billing.Payment':
                return False
                
            payment = Payment.objects.get(id=ledger_entry.external_reference_id)
            
            # Find Course purchases associated with this payment
            purchases = CoursePurchase.objects.filter(payment=payment).select_related('course', 'course__instructor')
            
            if not purchases.exists():
                return False
                
            with transaction.atomic():
                for purchase in purchases:
                    course = purchase.course
                    if not course or not course.instructor:
                        continue
                        
                    instructor = course.instructor
                    
                    # Look up personalized agreement or system default
                    agreement = RevenueShareAgreement.objects.filter(
                        instructor=instructor,
                        course=course,
                        is_active=True
                    ).first()
                    
                    if not agreement:
                        agreement = RevenueShareAgreement.objects.filter(
                            instructor=instructor,
                            course=None,
                            is_active=True
                        ).first()
                        
                    # Default system share (e.g., 30%)
                    share_bps = agreement.commission_bps if agreement else 3000 
                    
                    # Split proportional payment logic here
                    # For simplicity, assume single item payment amount maps fully to this line
                    gross = ledger_entry.amount_cents
                    
                    instructor_share = int(gross * (share_bps / 10000.0))
                    
                    InstructorCommission.objects.create(
                        instructor=instructor,
                        ledger_entry=ledger_entry,
                        gross_amount_cents=gross,
                        instructor_share_cents=instructor_share,
                        status='pending'
                    )
            return True
            
        except Exception as e:
            # Log warning, do not halt system transaction loop
            print(f"CRITICAL ANALYTICS ERROR during attribution: {e}")
            return False
