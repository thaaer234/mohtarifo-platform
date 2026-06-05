from datetime import timedelta

from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.devices import device_fingerprint
from billing.models import AccessGrant

from .models import Attempt, AttemptAnswer, Exam, QuestionOption
from .serializers import AttemptSerializer, ExamSerializer, QuestionSerializer


def _active_device_grants(request):
    now = timezone.now()
    if request and getattr(request, "session", None) and request.session.get("impersonator_admin_id"):
        return AccessGrant.objects.filter(user=request.user).filter(
            models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now),
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gte=now),
        )
    fingerprint = device_fingerprint(request)
    return AccessGrant.objects.filter(user=request.user).filter(
        models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now),
        models.Q(expires_at__isnull=True) | models.Q(expires_at__gte=now),
        models.Q(device_fingerprint="") | models.Q(device_fingerprint=fingerprint),
    )


def _user_can_access_exam(user, exam, request=None):
    if not user.is_authenticated:
        return False
    now = timezone.now()
    active_grants = _active_device_grants(request) if request is not None else AccessGrant.objects.filter(user=user).filter(
        models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now),
        models.Q(expires_at__isnull=True) | models.Q(expires_at__gte=now),
    )
    if active_grants.filter(course=exam.course).exists():
        return True
    if exam.lesson_id and active_grants.filter(lesson_id=exam.lesson_id).exists():
        return True
    return False


class ExamListApiView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ExamSerializer

    def get_queryset(self):
        active_grants = _active_device_grants(self.request)
        course_ids = active_grants.filter(
            course__isnull=False,
        ).values_list("course_id", flat=True)
        lesson_ids = active_grants.filter(
            lesson__isnull=False,
        ).values_list("lesson_id", flat=True)
        return (
            Exam.objects.filter(status="published")
            .filter(models.Q(course_id__in=course_ids) | models.Q(lesson_id__in=lesson_ids))
            .select_related("course")
            .order_by("-created_at")
        )


class ExamStartApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "exam_start"

    def post(self, request, exam_id):
        exam = get_object_or_404(
            Exam.objects.select_related("course").prefetch_related("questions__options"),
            id=exam_id,
            status="published",
        )
        if not _user_can_access_exam(request.user, exam, request):
            raise PermissionDenied("You do not have access to this exam.")

        attempt = Attempt.objects.create(
            user=request.user,
            exam=exam,
            expires_at=timezone.now() + timedelta(minutes=exam.duration_minutes),
            max_score=exam.question_count,
        )

        questions = exam.questions.filter(status="published").prefetch_related("options")[: exam.question_count]
        return Response(
            {
                "attempt_id": attempt.id,
                "exam": ExamSerializer(exam).data,
                "questions": QuestionSerializer(questions, many=True).data,
            }
        )


class AttemptSubmitApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "exam_submit"

    def post(self, request, attempt_id):
        attempt = get_object_or_404(
            Attempt.objects.select_related("exam", "exam__course"),
            id=attempt_id,
            user=request.user,
        )
        if attempt.status != "in_progress":
            raise ValidationError("This attempt is not in progress.")
        if attempt.expires_at < timezone.now():
            attempt.status = "expired"
            attempt.save(update_fields=["status", "updated_at"])
            raise ValidationError("This attempt has expired.")
        if not _user_can_access_exam(request.user, attempt.exam, request):
            raise PermissionDenied("You do not have access to this exam.")

        answers_payload = request.data.get("answers") or []
        if not answers_payload:
            selected_option_id = request.data.get("selected_option_id")
            question_id = request.data.get("question_id")
            answers_payload = [
                {
                    "question_id": question_id,
                    "selected_option_id": selected_option_id,
                    "time_seconds": request.data.get("time_seconds") or 0,
                }
            ]

        allowed_question_ids = set(attempt.exam.questions.values_list("id", flat=True))
        processed_answers = []
        for raw_answer in answers_payload:
            question_id = raw_answer.get("question_id")
            try:
                question_id = int(question_id)
            except (TypeError, ValueError):
                continue
            if question_id not in allowed_question_ids:
                continue

            selected_option_id = raw_answer.get("selected_option_id")
            selected_option = (
                QuestionOption.objects.filter(id=selected_option_id, question_id=question_id).first()
                if selected_option_id
                else None
            )
            is_correct = bool(selected_option and selected_option.is_correct)
            processed_answers.append(
                {
                    "question_id": question_id,
                    "selected_option": selected_option,
                    "is_correct": is_correct,
                    "time_seconds": int(raw_answer.get("time_seconds") or 0),
                }
            )

        total_questions = len(processed_answers) or 1
        correct_count = sum(1 for item in processed_answers if item["is_correct"])
        accuracy = round((correct_count / total_questions) * 100, 2)
        total_time_seconds = sum(item["time_seconds"] for item in processed_answers)

        AttemptAnswer.objects.filter(attempt=attempt).delete()
        for item in processed_answers:
            AttemptAnswer.objects.create(
                attempt=attempt,
                question_id=item["question_id"],
                selected_option=item["selected_option"],
                is_correct=item["is_correct"],
                time_seconds=item["time_seconds"],
            )
        attempt.status = "submitted"
        attempt.submitted_at = timezone.now()
        attempt.score = correct_count
        attempt.max_score = max(attempt.max_score, total_questions)
        attempt.accuracy = accuracy
        attempt.total_time_seconds = total_time_seconds
        attempt.save()

        return Response(
            {
                "attempt": AttemptSerializer(attempt).data,
                "next_action": {
                    "type": "exam" if correct_count == total_questions else "lesson",
                    "title": "Review your result" if correct_count == total_questions else "Review the related lesson",
                },
            },
            status=status.HTTP_200_OK,
        )
