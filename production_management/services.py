from datetime import timedelta
from django.utils import timezone
from .models import TeacherProductionSession, ProductionStatus, ProductionCost, ProductionTimeline

class SmartSchedulingEngine:
    """
    Auto Scheduling Engine
    Calculates best shooting dates, edit times, buffers, etc.
    """
    BUFFER_DAYS = {
        'science': 4,
        'literal': 3,
        'ninth': 2,
        'other': 2,
    }

    PRODUCTION_DURATION = {
        'science': {'shooting': 5, 'editing': 7, 'reviewing': 2, 'designing': 1, 'uploading': 1},
        'literal': {'shooting': 3, 'editing': 4, 'reviewing': 1, 'designing': 0.5, 'uploading': 0.5}, # Approximated as theory
        'ninth': {'shooting': 4, 'editing': 5, 'reviewing': 1, 'designing': 0.75, 'uploading': 0.5}, # Approximated as languages
        'other': {'shooting': 3, 'editing': 4, 'reviewing': 1, 'designing': 0.5, 'uploading': 0.5},
    }

    @classmethod
    def calculate_optimal_schedule(cls, exam_date, branch):
        buffer_days = cls.BUFFER_DAYS.get(branch, 2)
        target_ready_date = exam_date - timedelta(days=buffer_days)
        
        # Simple backward scheduling
        # Uploading: 1 day
        # Designing: 1 day
        # Reviewing: 1 day
        # Editing: 2 days
        # Shooting: 1 day
        
        shooting_date = target_ready_date - timedelta(days=6)
        return {
            'target_ready_date': target_ready_date,
            'recommended_shooting_date': shooting_date
        }

class ExamProgramScannerService:
    """
    AI + OCR Exam Program Scanner
    Uses Tesseract or PaddleOCR logic
    """
    @staticmethod
    def process_image(image_path):
        # Placeholder for OCR processing
        # 1. Tesseract OCR
        # 2. Rule-based AI Parsing
        # 3. Fuzzy Matching
        
        return [
            {
                'subject': 'الرياضيات',
                'branch': 'science',
                'exam_date': timezone.now().date() + timedelta(days=20)
            },
            {
                'subject': 'اللغة العربية',
                'branch': 'literal',
                'exam_date': timezone.now().date() + timedelta(days=15)
            }
        ]

    @staticmethod
    def auto_build_production_schedule(parsed_data):
        sessions = []
        for item in parsed_data:
            schedule = SmartSchedulingEngine.calculate_optimal_schedule(item['exam_date'], item['branch'])
            # Create session...
            sessions.append({
                'subject': item['subject'],
                'branch': item['branch'],
                'exam_date': item['exam_date'],
                'recommended_shooting_date': schedule['recommended_shooting_date']
            })
        return sessions
