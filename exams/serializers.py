from rest_framework import serializers

from .models import Attempt, Exam, Question, QuestionOption


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ["id", "body", "sort_order"]


class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)
    topic_name = serializers.CharField(source="topic.name", read_only=True)

    class Meta:
        model = Question
        fields = ["id", "body", "question_type", "difficulty", "topic_name", "options"]


class ExamSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = Exam
        fields = [
            "id",
            "title",
            "description",
            "course_title",
            "mode",
            "duration_minutes",
            "question_count",
            "status",
        ]


class AttemptSerializer(serializers.ModelSerializer):
    exam_title = serializers.CharField(source="exam.title", read_only=True)

    class Meta:
        model = Attempt
        fields = [
            "id",
            "exam",
            "exam_title",
            "status",
            "started_at",
            "submitted_at",
            "expires_at",
            "score",
            "max_score",
            "accuracy",
            "total_time_seconds",
        ]
