from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from analytics.services import AIService

from .models import Attempt, AttemptAnswer, Exam, QuestionOption
from .views import _user_can_access_exam


@login_required
def exam_detail(request, exam_id):
    exam = get_object_or_404(Exam.objects.select_related("course"), id=exam_id, status="published")
    if not _user_can_access_exam(request.user, exam, request):
        messages.error(request, "You do not have access to this exam.")
        return redirect("dashboard:student_dashboard")

    recent_attempts = Attempt.objects.filter(user=request.user, exam=exam).order_by("-created_at")[:5]

    return render(
        request,
        "exams/exam_detail.html",
        {
            "exam": exam,
            "recent_attempts": recent_attempts,
        },
    )


@login_required
def start_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, status="published")
    if not _user_can_access_exam(request.user, exam, request):
        messages.error(request, "You do not have access to this exam.")
        return redirect("dashboard:student_dashboard")

    attempt = Attempt.objects.create(
        user=request.user,
        exam=exam,
        status="in_progress",
        expires_at=timezone.now() + timedelta(minutes=exam.duration_minutes),
        max_score=exam.question_count,
    )

    return redirect("exams:solve_exam", attempt_id=attempt.id)


@login_required
def solve_exam(request, attempt_id):
    attempt = get_object_or_404(Attempt.objects.select_related("exam", "exam__course"), id=attempt_id, user=request.user)

    if not _user_can_access_exam(request.user, attempt.exam, request):
        messages.error(request, "You do not have access to this exam.")
        return redirect("dashboard:student_dashboard")

    if attempt.status != "in_progress" or attempt.expires_at < timezone.now():
        return redirect("exams:exam_result", attempt_id=attempt.id)

    exam = attempt.exam
    questions = exam.questions.filter(status="published").prefetch_related("options")

    if request.method == "POST":
        score = 0
        total = 0
        AttemptAnswer.objects.filter(attempt=attempt).delete()
        for question in questions:
            option_id = request.POST.get(f"question_{question.id}")
            if option_id:
                option = QuestionOption.objects.filter(id=option_id, question=question).first()
                is_correct = bool(option and option.is_correct)
                if is_correct:
                    score += 1

                AttemptAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_option=option,
                    is_correct=is_correct,
                )
            total += 1

        attempt.status = "submitted"
        attempt.submitted_at = timezone.now()
        attempt.score = score
        attempt.max_score = total
        attempt.accuracy = (score / total * 100) if total > 0 else 0
        attempt.save()

        AIService.update_performance_from_attempt(attempt)

        return redirect("exams:exam_result", attempt_id=attempt.id)

    return render(
        request,
        "exams/solve_exam.html",
        {
            "attempt": attempt,
            "exam": exam,
            "questions": questions,
        },
    )


@login_required
def exam_result(request, attempt_id):
    attempt = get_object_or_404(Attempt.objects.select_related("exam"), id=attempt_id, user=request.user)
    answers = attempt.answers.select_related("question").prefetch_related("question__options")

    return render(
        request,
        "exams/exam_result.html",
        {
            "attempt": attempt,
            "answers": answers,
        },
    )
