from django.utils import timezone
from datetime import timedelta
from django.db import models
from .models import StudyPlan, StudyPlanItem, TopicPerformance
from learning.models import Lesson, Course
from exams.models import Attempt

class AIService:
    @staticmethod
    def generate_smart_study_plan(user, course):
        """
        Analyzes the user's performance in a course and generates a tailored study plan.
        Focuses on topics with low accuracy and high importance.
        """
        # 1. Fetch performance data
        performances = TopicPerformance.objects.filter(user=user, topic__subject=course.subject).order_by('accuracy')
        
        # 2. Create the plan
        plan_title = f"خطة ذكية: {course.title} - {timezone.now().strftime('%Y-%m-%d')}"
        plan = StudyPlan.objects.create(
            user=user,
            title=plan_title,
            starts_at=timezone.now().date(),
            ends_at=(timezone.now() + timedelta(days=14)).date(),
            status="active"
        )
        
        # 3. Prioritize weak topics
        weak_topics = performances.filter(accuracy__lt=60)[:5]
        
        # 4. Add items to the plan
        day_offset = 0
        for perf in weak_topics:
            # Find a lesson related to this topic
            lesson = Lesson.objects.filter(topics=perf.topic, unit__course=course).first()
            if lesson:
                StudyPlanItem.objects.create(
                    study_plan=plan,
                    item_type="lesson",
                    lesson=lesson,
                    topic=perf.topic,
                    title=f"مراجعة: {perf.topic.name}",
                    due_date=timezone.now().date() + timedelta(days=day_offset),
                    estimated_minutes=45,
                    sort_order=day_offset
                )
                day_offset += 1
                
        # 5. Add a final review quiz
        StudyPlanItem.objects.create(
            study_plan=plan,
            item_type="review",
            title="اختبار تقييمي شامل للمكثفة",
            due_date=timezone.now().date() + timedelta(days=day_offset),
            estimated_minutes=60,
            sort_order=day_offset
        )
        
        return plan

    @staticmethod
    def update_performance_from_attempt(attempt):
        """
        Updates TopicPerformance records based on the results of an exam attempt.
        """
        user = attempt.user
        answers = attempt.answers.select_related('question__topic')
        
        topic_results = {}
        for ans in answers:
            topic = ans.question.topic
            if topic not in topic_results:
                topic_results[topic] = {'correct': 0, 'total': 0, 'time': 0}
            
            topic_results[topic]['total'] += 1
            if ans.is_correct:
                topic_results[topic]['correct'] += 1
            topic_results[topic]['time'] += ans.time_seconds
            
        for topic, stats in topic_results.items():
            perf, created = TopicPerformance.objects.get_or_create(user=user, topic=topic)
            
            # Update counts
            perf.attempts_count += stats['total']
            perf.correct_count += stats['correct']
            perf.wrong_count += (stats['total'] - stats['correct'])
            
            # Recalculate accuracy
            total = perf.correct_count + perf.wrong_count
            if total > 0:
                perf.accuracy = (perf.correct_count / total) * 100
                
            # Average time
            if stats['total'] > 0:
                new_avg = stats['time'] / stats['total']
                perf.avg_time_seconds = (perf.avg_time_seconds + new_avg) / 2
                
            # Mastery logic (simple version)
            perf.mastery_score = (perf.accuracy * 0.7) + (min(perf.attempts_count, 10) * 3)
            perf.last_practiced_at = timezone.now()
            perf.save()


class TrackingService:
    @staticmethod
    def log_landing_visit(request):
        """
        Silently logs visitor information for analytical visibility.
        Uses raw user-agent parsing.
        """
        try:
            from .models import LandingVisit
            import user_agents
            
            ua_string = request.META.get('HTTP_USER_AGENT', '')
            user_agent = user_agents.parse(ua_string)
            
            # Categorize device
            device_type = "pc"
            if user_agent.is_mobile:
                device_type = "mobile"
            elif user_agent.is_tablet:
                device_type = "tablet"
            elif user_agent.is_bot:
                device_type = "bot"
                
            # Extract IP Address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
                
            # Prepare logic safely
            user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
            
            if hasattr(request, 'session'):
                session_key = request.session.session_key
                if not session_key:
                    # Trigger session saving if not initialized yet
                    request.session.save()
                    session_key = request.session.session_key
            else:
                session_key = f"ip_{ip}"
                
            # Prevent spamming: Check if we logged this session in the last 5 seconds
            from django.utils import timezone
            recent = LandingVisit.objects.filter(session_key=session_key).order_by('-visited_at').first()
            if recent and (timezone.now() - recent.visited_at).total_seconds() < 5:
                if user and not recent.user:
                    recent.user = user
                    recent.save(update_fields=['user'])
                return
                
            LandingVisit.objects.create(
                user=user,
                session_key=session_key,
                ip_address=ip,
                user_agent=ua_string[:400] if ua_string else None,
                device_type=device_type,
                os_family=user_agent.os.family,
                browser_family=user_agent.browser.family
            )
        except Exception as e:
            import traceback
            import sys
            try:
                with open("landing_error_log.txt", "a") as f:
                    f.write(traceback.format_exc() + "\n")
            except:
                pass
            pass
