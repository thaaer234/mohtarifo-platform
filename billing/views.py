from django.db import transaction
from django.db import models
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .devices import device_fingerprint
from .models import AccessCode, AccessGrant, Subscription
from .serializers import AccessGrantSerializer, RedeemAccessCodeSerializer


class RedeemAccessCodeApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "billing_redeem"

    def post(self, request):
        serializer = RedeemAccessCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code_value = serializer.validated_data["code"].strip().upper()
        user = request.user
        current_device = device_fingerprint(request)

        with transaction.atomic():
            access_code = AccessCode.objects.select_for_update().filter(code__iexact=code_value).first()
            if access_code is None:
                return Response({"detail": "Invalid access code."}, status=status.HTTP_404_NOT_FOUND)

            allowed, reason = access_code.is_redeemable(timezone.now())
            if not allowed:
                return Response({"detail": reason}, status=status.HTTP_400_BAD_REQUEST)

            package_grants = []
            if access_code.access_type == "package" and access_code.package:
                package_courses = list(access_code.package.eligible_courses_queryset().select_related("subject", "instructor"))
                grouped_courses = {}
                for course in package_courses:
                    grouped_courses.setdefault(course.subject_id, []).append(course)
                ambiguous_subjects = [
                    courses[0].subject.name
                    for courses in grouped_courses.values()
                    if len(courses) > 1
                ]
                if ambiguous_subjects:
                    return Response(
                        {
                            "detail": "Package requires course selection.",
                            "requires_selection": True,
                            "subjects": ambiguous_subjects,
                        },
                        status=status.HTTP_409_CONFLICT,
                    )
                for course in package_courses:
                    grant, _created = AccessGrant.objects.get_or_create(
                        user=user,
                        course=course,
                        lesson=None,
                        defaults={
                            "access_code": access_code,
                            "source": "code",
                            "device_fingerprint": current_device,
                            "starts_at": timezone.now(),
                            "expires_at": access_code.valid_until,
                        },
                    )
                    if grant.device_fingerprint and grant.device_fingerprint != current_device:
                        return Response(
                            {"detail": "This access is linked to another device. Contact support to move it."},
                            status=status.HTTP_403_FORBIDDEN,
                        )
                    if not grant.device_fingerprint:
                        grant.device_fingerprint = current_device
                        grant.save(update_fields=["device_fingerprint"])
                    package_grants.append(grant)
                access_code.redeemed_count += 1
                access_code.save(update_fields=["redeemed_count", "updated_at"])
                return Response(
                    {"detail": "Package access code redeemed successfully.", "grants": AccessGrantSerializer(package_grants, many=True).data},
                    status=status.HTTP_201_CREATED,
                )

            grant, created = AccessGrant.objects.get_or_create(
                user=user,
                course=access_code.course,
                lesson=access_code.lesson,
                defaults={
                    "access_code": access_code,
                    "source": "code",
                    "device_fingerprint": current_device,
                    "starts_at": timezone.now(),
                    "expires_at": access_code.valid_until,
                },
            )

            if not created:
                if grant.device_fingerprint and grant.device_fingerprint != current_device:
                    return Response(
                        {"detail": "This access is linked to another device. Contact support to move it."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                if not grant.device_fingerprint:
                    grant.device_fingerprint = current_device
                    grant.save(update_fields=["device_fingerprint"])
                return Response(
                    {"detail": "User already has this access.", "grant": AccessGrantSerializer(grant).data},
                    status=status.HTTP_200_OK,
                )

            access_code.redeemed_count += 1
            access_code.save(update_fields=["redeemed_count", "updated_at"])

            if access_code.access_type == "subscription" and access_code.plan:
                Subscription.objects.get_or_create(
                    user=user,
                    plan=access_code.plan,
                    defaults={
                        "provider": "access_code",
                        "provider_subscription_id": access_code.code,
                        "status": "active",
                        "starts_at": timezone.now(),
                        "ends_at": access_code.valid_until,
                    },
                )

        return Response(
            {"detail": "Access code redeemed successfully.", "grant": AccessGrantSerializer(grant).data},
            status=status.HTTP_201_CREATED,
        )


class MyAccessGrantsApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        current_device = device_fingerprint(request)
        grants = (
            AccessGrant.objects.filter(user=request.user)
            .filter(models.Q(device_fingerprint="") | models.Q(device_fingerprint=current_device))
            .select_related("course", "lesson", "access_code")
            .order_by("-created_at")
        )
        return Response(AccessGrantSerializer(grants, many=True).data)
