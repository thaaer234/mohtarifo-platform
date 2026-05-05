from rest_framework import serializers

from .models import StudyPlan, StudyPlanItem, TopicPerformance


class TopicPerformanceSerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(source="topic.name", read_only=True)

    class Meta:
        model = TopicPerformance
        fields = [
            "id",
            "topic",
            "topic_name",
            "attempts_count",
            "correct_count",
            "wrong_count",
            "accuracy",
            "avg_time_seconds",
            "mastery_score",
            "last_practiced_at",
        ]


class StudyPlanItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyPlanItem
        fields = [
            "id",
            "item_type",
            "title",
            "due_date",
            "estimated_minutes",
            "completed_at",
            "sort_order",
        ]


class StudyPlanSerializer(serializers.ModelSerializer):
    items = StudyPlanItemSerializer(many=True, read_only=True)

    class Meta:
        model = StudyPlan
        fields = ["id", "title", "starts_at", "ends_at", "status", "items"]
