from rest_framework import serializers

from .models import AccessCode, AccessGrant


class RedeemAccessCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=80)


class AccessGrantSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)
    code = serializers.CharField(source="access_code.code", read_only=True)

    class Meta:
        model = AccessGrant
        fields = [
            "id",
            "course",
            "course_title",
            "lesson",
            "lesson_title",
            "source",
            "code",
            "starts_at",
            "expires_at",
            "created_at",
        ]


class AccessCodeSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)

    class Meta:
        model = AccessCode
        fields = [
            "id",
            "code",
            "access_type",
            "course_title",
            "lesson_title",
            "max_redemptions",
            "redeemed_count",
            "valid_until",
            "status",
        ]
