from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from billing.models import AccessGrant
from learning.models import Course, Subject, Topic

from .models import Exam, ExamQuestion, Question, QuestionOption


class ExamApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.instructor = user_model.objects.create_user(username="teacher", password="teacher12345")
        self.student = user_model.objects.create_user(username="student", password="student12345")
        subject = Subject.objects.create(name="Math", slug="math")
        self.course = Course.objects.create(
            subject=subject,
            instructor=self.instructor,
            title="Limits Intensive",
            slug="limits-intensive",
            description="Test course",
            status="published",
        )
        topic = Topic.objects.create(subject=subject, course=self.course, name="Limits", slug="limits")
        self.exam = Exam.objects.create(course=self.course, title="Exam 1", question_count=2, status="published")
        q1 = Question.objects.create(topic=topic, author=self.instructor, body="1+1?", status="published")
        q2 = Question.objects.create(topic=topic, author=self.instructor, body="2+2?", status="published")
        self.q1_correct = QuestionOption.objects.create(question=q1, body="2", is_correct=True, sort_order=1)
        QuestionOption.objects.create(question=q1, body="3", is_correct=False, sort_order=2)
        self.q2_correct = QuestionOption.objects.create(question=q2, body="4", is_correct=True, sort_order=1)
        QuestionOption.objects.create(question=q2, body="5", is_correct=False, sort_order=2)
        ExamQuestion.objects.create(exam=self.exam, question=q1, points=1, sort_order=1)
        ExamQuestion.objects.create(exam=self.exam, question=q2, points=1, sort_order=2)

    def test_exam_list_endpoint_requires_authentication(self):
        response = self.client.get(reverse("exams:exam_list"))
        self.assertEqual(response.status_code, 403)

    def test_start_and_submit_exam_scores_all_answers(self):
        AccessGrant.objects.create(user=self.student, course=self.course, source="admin")
        self.client.force_authenticate(user=self.student)
        start_response = self.client.post(reverse("exams:exam_start", args=[self.exam.id]), {}, format="json")
        self.assertEqual(start_response.status_code, 200)
        attempt_id = start_response.data["attempt_id"]
        questions = start_response.data["questions"]
        self.assertNotIn("is_correct", questions[0]["options"][0])

        submit_response = self.client.post(
            reverse("exams:attempt_submit", args=[attempt_id]),
            {
                "answers": [
                    {
                        "question_id": questions[0]["id"],
                        "selected_option_id": self.q1_correct.id,
                        "time_seconds": 20,
                    },
                    {
                        "question_id": questions[1]["id"],
                        "selected_option_id": self.q2_correct.id,
                        "time_seconds": 30,
                    },
                ]
            },
            format="json",
        )
        self.assertEqual(submit_response.status_code, 200)
        self.assertEqual(submit_response.data["attempt"]["score"], 2)
        self.assertEqual(submit_response.data["attempt"]["max_score"], 2)
        self.assertEqual(float(submit_response.data["attempt"]["accuracy"]), 100.0)
