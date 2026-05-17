from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.devices import activate_user_device

from .auth_utils import resolve_user_for_login, verify_instructor_password


class AuthCsrfApiView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        token = get_token(request)
        return Response({"csrf_token": token}, status=status.HTTP_200_OK)


@method_decorator(csrf_protect, name="dispatch")
class AuthLoginApiView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = "auth_login"

    def post(self, request):
        raw_username = (request.data.get("username") or "").strip()
        password = request.data.get("password")
        if not raw_username or not password:
            return Response({"detail": "username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        user = resolve_user_for_login(raw_username)
        if user and hasattr(user, "instructor_profile"):
            if not verify_instructor_password(user, password):
                user = None
        elif user:
            user = authenticate(request, username=user.username, password=password)
        if not user:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        login(request, user)
        
        # تحضير البيانات الأساسية للاستجابة
        response_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_staff": user.is_staff,
            "force_password_change": False,  # القيمة الافتراضية
        }
        
        # التحقق من ما إذا كان المستخدم مدرساً وهل يحتاج لتغيير كلمة المرور
        if hasattr(user, 'instructor_profile'):
            response_data["force_password_change"] = user.instructor_profile.force_password_change
        
        response = Response(response_data, status=status.HTTP_200_OK)
        
        if not user.is_staff:
            activate_user_device(request, user, response)
        return response


@method_decorator(csrf_protect, name="dispatch")
class AuthLogoutApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Logged out."}, status=status.HTTP_200_OK)


class AuthMeApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_staff": user.is_staff,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_protect, name="dispatch")
class InstructorChangePasswordApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """
        تغيير كلمة المرور للمدرس وإزالة العلم force_password_change
        """
        user = request.user
        
        # التحقق من أن المستخدم لديه ملف مدرس
        if not hasattr(user, 'instructor_profile'):
            return Response(
                {"detail": "المستخدم ليس مدرساً"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        old_password = request.data.get("old_password", "").strip()
        new_password = request.data.get("new_password", "").strip()
        confirm_password = request.data.get("confirm_password", "").strip()
        
        # التحقق من المدخلات
        if not old_password:
            return Response(
                {"detail": "كلمة المرور الحالية مطلوبة"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not new_password or not confirm_password:
            return Response(
                {"detail": "كلمة المرور الجديدة وتأكيدها مطلوبة"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_password != confirm_password:
            return Response(
                {"detail": "كلمات المرور الجديدة غير متطابقة"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_password) < 8:
            return Response(
                {"detail": "كلمة المرور يجب أن تكون 8 خانات على الأقل"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # التحقق من كلمة المرور الحالية
        if not user.check_password(old_password):
            return Response(
                {"detail": "كلمة المرور الحالية غير صحيحة"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # تغيير كلمة المرور
        user.set_password(new_password)
        user.save()
        
        # إزالة العلم الذي يجبر على تغيير كلمة المرور
        instructor_profile = user.instructor_profile
        instructor_profile.force_password_change = False
        instructor_profile.save()
        
        # إعادة توثيق المستخدم بـ كلمة المرور الجديدة
        user = authenticate(request, username=user.username, password=new_password)
        if user:
            login(request, user)
        
        request.session.pop("instructor_password_modal_dismissed", None)

        return Response(
            {
                "detail": "تم تغيير كلمة المرور بنجاح",
                "force_password_change": False
            },
            status=status.HTTP_200_OK
        )


@method_decorator(csrf_protect, name="dispatch")
class InstructorDismissPasswordReminderApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not hasattr(request.user, "instructor_profile"):
            return Response({"detail": "المستخدم ليس مدرساً"}, status=status.HTTP_403_FORBIDDEN)
        request.session["instructor_password_modal_dismissed"] = True
        return Response({"detail": "تم التخطي. يرجى تغيير كلمة المرور من الإعدادات قريباً."}, status=status.HTTP_200_OK)
