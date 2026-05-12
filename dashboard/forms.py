from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from accounts.models import AcademicBranch, Governorate, InstructorProfile
from billing.models import AccessCode, AccessCodeBatch, CoursePackage, Institute, SalesCenter
from learning.models import Course, Lesson, Subject, Unit
from .models import CatalogSection
from .security import sanitize_plain_text, validate_syrian_mobile


def _user_display_label(user):
    full_name = (user.get_full_name() or "").strip()
    label = full_name or user.username
    if user.username and user.username != label:
        return f"{label} - {user.username}"
    return label


def _course_display_label(course):
    instructor = _user_display_label(course.instructor) if getattr(course, "instructor_id", None) else "بدون مدرس"
    subject = course.subject.name if getattr(course, "subject_id", None) else "بدون مادة"
    return f"{course.title} - {subject} - {instructor}"


class StudentRegistrationForm(UserCreationForm):
    first_name = forms.CharField(label="الاسم الكامل", max_length=120)
    username = forms.CharField(label="رقم الهاتف", max_length=40)
    track = forms.ChoiceField(label="الفرع", choices=[])
    governorate = forms.ChoiceField(label="المحافظة", choices=[])
    gender = forms.ChoiceField(label="الجنس", choices=[])
    email = forms.EmailField(label="البريد الإلكتروني", required=False)

    class Meta:
        model = User
        fields = ["first_name", "username", "track", "governorate", "gender", "email", "password1", "password2"]
        labels = {
            "username": "رقم الهاتف",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "first_name": "أدخل الاسم الكامل",
            "username": "09xxxxxxxx",
            "email": "اختياري",
            "password1": "كلمة المرور",
            "password2": "تأكيد كلمة المرور",
        }
        for name, field in self.fields.items():
            if name in placeholders:
                field.widget.attrs["placeholder"] = placeholders[name]
        branch_choices = [("", "اختر الفرع")] + [
            (branch.name, branch.name) for branch in AcademicBranch.objects.filter(is_active=True)
        ]
        governorate_choices = [("", "اختر المحافظة")] + [
            (governorate.name, governorate.name) for governorate in Governorate.objects.filter(is_active=True)
        ]
        gender_choices = [("", "حدد الجنس"), ("male", "ذكر"), ("female", "أنثى")]
        
        self.fields["track"].choices = branch_choices
        self.fields["governorate"].choices = governorate_choices
        self.fields["gender"].choices = gender_choices

    def clean_first_name(self):
        value = sanitize_plain_text(self.cleaned_data["first_name"], max_length=120)
        if not value:
            raise ValidationError("الرجاء إدخال الاسم الكامل.")
        
        # 1. Ensure only Arabic letters and spaces are allowed
        import re
        arabic_pattern = re.compile(r'^[\u0621-\u064A\u0622\u0623\u0624\u0625\u0626\u0629\u0649\s]+$')
        if not arabic_pattern.match(value):
            raise ValidationError("يجب كتابة الاسم الكامل باللغة العربية فقط وبدون أرقام أو رموز.")
        
        # 2. Prevent consecutive letter repetitions (e.g., "ببب", "سسس", "هههه")
        if re.search(r'(.)\1\1', value):
            raise ValidationError("الرجاء إدخال اسم حقيقي وتجنب تكرار الأحرف بشكل عشوائي.")
            
        # 3. Ensure the name contains at least two words (First Name and Family Name)
        parts = [p.strip() for p in value.split() if p.strip()]
        if len(parts) < 2:
            raise ValidationError("الرجاء إدخال الاسم الكامل ثنائياً على الأقل (الاسم والكنية).")
            
        # 4. Ensure each part/word is at least 2 characters long to avoid single letters
        for part in parts:
            if len(part) < 2:
                raise ValidationError("يجب أن يتكون كل جزء من الاسم من حرفين على الأقل لتأكيد مصداقيته.")
                
        return value

    def clean_username(self):
        return validate_syrian_mobile(self.cleaned_data["username"])

    def clean_track(self):
        value = self.cleaned_data["track"]
        if not value:
            raise ValidationError("اختر الفرع.")
        return sanitize_plain_text(value, max_length=80)

    def clean_governorate(self):
        value = self.cleaned_data["governorate"]
        if not value:
            raise ValidationError("اختر المحافظة.")
        return sanitize_plain_text(value, max_length=80)

    def clean_gender(self):
        value = self.cleaned_data["gender"]
        if not value:
            raise ValidationError("يرجى تحديد الجنس (ذكر / أنثى).")
        return value

    def save(self, commit=True):
        user = super().save(commit=False)
        user.last_name = ""
        user.email = self.cleaned_data.get("email", "")
        if commit:
            user.save()
        return user


class RedeemCodeForm(forms.Form):
    code = forms.CharField(label="كود المادة أو الدرس", max_length=80)


class CourseCreateForm(forms.ModelForm):
    subject = forms.ModelChoiceField(label="المادة", queryset=Subject.objects.order_by("name"), required=False)
    new_subject = forms.CharField(label="مادة جديدة", max_length=120, required=False)
    new_instructor_name = forms.CharField(label="اسم مدرس جديد", max_length=120, required=False)
    new_instructor_phone = forms.CharField(label="هاتف المدرس الجديد", max_length=40, required=False)
    new_instructor_specialty = forms.CharField(label="اختصاص المدرس الجديد", max_length=120, required=False)
    price_amount = forms.DecimalField(label="السعر", min_value=0, max_digits=12, decimal_places=2, required=False)

    class Meta:
        model = Course
        fields = [
            "kind",
            "academic_track",
            "term",
            "subject",
            "new_subject",
            "instructor",
            "new_instructor_name",
            "new_instructor_phone",
            "new_instructor_specialty",
            "title",
            "description",
            "price_amount",
            "cover",
            "status",
        ]
        labels = {
            "kind": "نوع المحتوى",
            "academic_track": "الفرع",
            "term": "الفصل",
            "instructor": "الأستاذ",
            "new_instructor_name": "اسم مدرس جديد",
            "new_instructor_phone": "هاتف المدرس الجديد",
            "new_instructor_specialty": "اختصاص المدرس الجديد",
            "title": "اسم المكثفة أو الدورة",
            "description": "وصف مختصر",
            "cover": "غلاف اختياري",
            "status": "حالة النشر",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["instructor"].queryset = (
            User.objects.filter(instructor_profile__status="active")
            .distinct()
            .order_by("first_name", "last_name", "username")
        )
        self.fields["instructor"].label_from_instance = _user_display_label
        self.fields["instructor"].required = False
        self.fields["instructor"].empty_label = "اختر مدرس موجود أو أضف مدرس جديد"
        self.fields["description"].required = False
        self.fields["cover"].required = False
        self.fields["status"].initial = "draft"

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("subject") and not cleaned.get("new_subject"):
            raise forms.ValidationError("اختر مادة موجودة أو اكتب مادة جديدة.")
        if not cleaned.get("instructor") and not cleaned.get("new_instructor_name"):
            raise forms.ValidationError("اختر مدرس موجود أو اكتب اسم مدرس جديد.")
        if cleaned.get("new_instructor_name"):
            phone = (cleaned.get("new_instructor_phone") or "").strip()
            if phone and User.objects.filter(username=phone).exists():
                raise forms.ValidationError("رقم هاتف المدرس موجود مسبقاً. اختر المدرس من القائمة أو استخدم رقم آخر.")
        return cleaned

    def save(self, commit=True):
        course = super().save(commit=False)
        new_instructor_name = self.cleaned_data.get("new_instructor_name", "").strip()
        if new_instructor_name:
            raw_phone = (self.cleaned_data.get("new_instructor_phone") or "").strip()
            username = raw_phone or slugify(new_instructor_name, allow_unicode=False) or "teacher"
            base_username = username
            counter = 2
            while User.objects.filter(username=username).exists():
                username = f"{base_username}-{counter}"
                counter += 1
            name_parts = new_instructor_name.split(" ", 1)
            instructor = User.objects.create_user(
                username=username,
                password=None,
                first_name=name_parts[0],
                last_name=name_parts[1] if len(name_parts) > 1 else "",
                is_staff=True,
            )
            InstructorProfile.objects.update_or_create(
                user=instructor,
                defaults={
                    "specialty": self.cleaned_data.get("new_instructor_specialty") or "",
                    "status": "active",
                },
            )
            course.instructor = instructor
        subject = self.cleaned_data.get("subject")
        new_subject = self.cleaned_data.get("new_subject", "").strip()
        if new_subject:
            subject_slug = slugify(new_subject, allow_unicode=True) or f"subject-{Subject.objects.count() + 1}"
            subject, _created = Subject.objects.get_or_create(name=new_subject, defaults={"slug": subject_slug})
        course.subject = subject
        price_amount = self.cleaned_data.get("price_amount")
        course.price_cents = int(price_amount * 100) if price_amount is not None else None
        base_slug = slugify(course.title, allow_unicode=True) or "course"
        slug = base_slug
        counter = 2
        while Course.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        course.slug = slug
        if commit:
            course.save()
            Unit.objects.get_or_create(course=course, title="الوحدة الأولى", defaults={"sort_order": 1})
        return course


class CourseCardMediaForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["cover", "pdf_file", "allow_pdf_download"]
        labels = {
            "cover": "غلاف كرت الدورة",
            "pdf_file": "ملف الـ PDF الخاص بالدورة كاملة",
            "allow_pdf_download": "السماح للطلاب بتنزيل الملف (PDF)؟",
        }
        help_texts = {
            "cover": "اختياري. إذا تركته فارغا سيتم استخدام صورة باسم الأستاذ من static/dashboard/course-covers/.",
            "pdf_file": "قم برفع ملف PDF واحد يشمل كامل الدورة.",
            "allow_pdf_download": "إذا تم التفعيل، سيتمكن الطالب من تحميل الملف على جهازه، وإلا فسيشاهده فقط داخل المنصة بشكل آمن.",
        }



class CourseEditForm(forms.ModelForm):
    price_amount = forms.DecimalField(label="السعر (ل.س)", min_value=0, max_digits=12, decimal_places=0, required=False)

    class Meta:
        model = Course
        fields = [
            "title",
            "subject",
            "instructor",
            "kind",
            "academic_track",
            "term",
            "status",
            "price_amount",
            "description",
        ]
        labels = {
            "title": "اسم الدورة",
            "subject": "المادة",
            "instructor": "الأستاذ",
            "kind": "نوع المحتوى",
            "academic_track": "الفرع الدراسي",
            "term": "الفصل الدراسي",
            "status": "حالة النشر",
            "price_amount": "السعر (ل.س)",
            "description": "الوصف المختصر",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["instructor"].queryset = (
            User.objects.filter(instructor_profile__status="active")
            .distinct()
            .order_by("first_name", "last_name", "username")
        )
        self.fields["instructor"].label_from_instance = _user_display_label
        self.fields["subject"].queryset = Subject.objects.order_by("name")
        self.fields["description"].required = False
        
        if self.instance and self.instance.pk:
            if self.instance.price_cents is not None:
                self.initial["price_amount"] = self.instance.price_cents / 100

    def save(self, commit=True):
        course = super().save(commit=False)
        price_amount = self.cleaned_data.get("price_amount")
        course.price_cents = int(price_amount * 100) if price_amount is not None else None
        
        # Regenerate slug if title changed and keep it unique
        base_slug = slugify(course.title, allow_unicode=True) or "course"
        if course.slug != base_slug:
            slug = base_slug
            counter = 2
            while Course.objects.filter(slug=slug).exclude(id=course.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            course.slug = slug

        if commit:
            course.save()
        return course


class CourseCodeBatchForm(forms.ModelForm):
    class Meta:
        model = AccessCodeBatch
        fields = ["name", "institute", "sales_center", "allocated_count", "free_count", "code_prefix", "notes"]
        labels = {
            "name": "اسم دفعة الأكواد",
            "institute": "المعهد",
            "sales_center": "مركز البيع",
            "allocated_count": "الرصيد المتوقع",
            "free_count": "عدد الأكواد المجانية",
            "code_prefix": "بادئة الكود",
            "notes": "ملاحظات",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["institute"].queryset = Institute.objects.filter(is_active=True)
        self.fields["sales_center"].queryset = SalesCenter.objects.filter(is_active=True)
        self.fields["institute"].required = False
        self.fields["sales_center"].required = False
        self.fields["notes"].required = False


class PackageCodeBatchForm(CourseCodeBatchForm):
    quantity = forms.IntegerField(label="عدد الأكواد", min_value=1, initial=10)
    free_codes = forms.BooleanField(label="أكواد مجانية", required=False, initial=False)

    class Meta(CourseCodeBatchForm.Meta):
        fields = ["name", "institute", "sales_center", "quantity", "free_codes", "code_prefix", "notes"]
        labels = {
            **CourseCodeBatchForm.Meta.labels,
            "quantity": "عدد الأكواد",
            "free_codes": "أكواد مجانية",
        }


class CourseStudentImportForm(forms.Form):
    batch = forms.ModelChoiceField(label="دفعة الأكواد", queryset=AccessCodeBatch.objects.none())
    file = forms.FileField(label="ملف الطلاب CSV/XLSX")
    free_codes = forms.BooleanField(label="أكواد مجانية", required=False, initial=True)

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        if course is not None:
            self.fields["batch"].queryset = AccessCodeBatch.objects.filter(course=course).order_by("-created_at")


class CourseLessonUploadForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["unit", "lesson_type", "title", "description", "video_url", "video_file", "pdf_file", "duration_seconds", "sort_order"]
        labels = {
            "unit": "الوحدة / الجلسة",
            "lesson_type": "نوع القسم",
            "title": "عنوان القسم",
            "description": "وصف مختصر",
            "video_url": "رابط Bunny.net (أو رابط خارجي)",
            "video_file": "أو رفع ملف فيديو محمي",
            "pdf_file": "رفع ملف الدرس (PDF المؤمن)",
            "duration_seconds": "مدة الفيديو بالثواني",
            "sort_order": "الترتيب",
        }

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = False
        self.fields["duration_seconds"].required = False
        self.fields["sort_order"].required = False
        self.fields["video_file"].required = False
        self.fields["video_url"].required = False
        self.fields["pdf_file"].required = False
        if course is not None:
            self.fields["unit"].queryset = course.units.order_by("sort_order", "id")

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("video_file") and not cleaned.get("video_url") and not cleaned.get("pdf_file"):
            raise forms.ValidationError("يجب رفع ملف PDF، أو إرفاق فيديو، أو وضع رابط فيديو واحد على الأقل.")
        return cleaned


class CourseCodeSaleForm(forms.Form):
    code = forms.ModelChoiceField(label="الكود", queryset=AccessCode.objects.none())
    student_name = forms.CharField(label="اسم الطالب", max_length=160)
    student_phone = forms.CharField(label="رقم الطالب", max_length=40)
    price_amount = forms.DecimalField(label="قيمة البيع", min_value=0, decimal_places=0, required=False)

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        if course is not None:
            self.fields["code"].queryset = (
                AccessCode.objects.filter(course=course, status="active", sale_status__in=["available", "reserved"])
                .order_by("created_at")
            )
        self.fields["price_amount"].required = False


class CourseUnitQuickForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ["title", "description", "sort_order"]
        labels = {
            "title": "اسم الجلسة",
            "description": "وصف مختصر",
            "sort_order": "ترتيب الجلسة",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = False
        self.fields["sort_order"].required = False


class InstituteForm(forms.ModelForm):
    class Meta:
        model = Institute
        fields = ["name", "contact_name", "phone", "logo", "notes", "is_active"]
        labels = {
            "name": "اسم المعهد",
            "contact_name": "اسم المسؤول",
            "phone": "رقم التواصل",
            "logo": "شعار المعهد",
            "notes": "ملاحظات",
            "is_active": "نشط",
        }


class SalesCenterForm(forms.ModelForm):
    class Meta:
        model = SalesCenter
        fields = ["name", "institute", "phone", "address", "is_active"]
        labels = {
            "name": "اسم مركز البيع",
            "institute": "المعهد المرتبط",
            "phone": "رقم التواصل",
            "address": "العنوان",
            "is_active": "نشط",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["institute"].queryset = Institute.objects.filter(is_active=True)
        self.fields["institute"].required = False


class PartnerBatchForm(forms.Form):
    course = forms.ModelChoiceField(label="الدورة", queryset=Course.objects.select_related("subject", "instructor").order_by("-created_at"))
    name = forms.CharField(label="اسم الدفعة", max_length=160)
    quantity = forms.IntegerField(label="عدد الأكواد", min_value=0, initial=0)
    code_prefix = forms.CharField(label="بادئة الكود", max_length=24, required=False)
    notes = forms.CharField(label="ملاحظات", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].label_from_instance = _course_display_label


class CoursePackageForm(forms.ModelForm):
    price_amount = forms.DecimalField(label="سعر الباقة", min_value=0, max_digits=12, decimal_places=0, required=False)

    class Meta:
        model = CoursePackage
        fields = ["name", "code", "package_track", "auto_include_shared", "courses", "price_amount", "is_active", "notes"]
        labels = {
            "name": "اسم الباقة",
            "code": "رمز الباقة",
            "package_track": "فرع الباقة",
            "auto_include_shared": "إضافة المواد المشتركة تلقائياً",
            "courses": "الدورات داخل الباقة",
            "is_active": "فعالة",
            "notes": "ملاحظات",
        }
        widgets = {
            "courses": forms.CheckboxSelectMultiple,
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["courses"].queryset = Course.objects.select_related("subject", "instructor").order_by("academic_track", "subject__name", "title")
        self.fields["courses"].label_from_instance = _course_display_label
        self.fields["courses"].required = False
        self.fields["courses"].help_text = "يُستخدم فقط عند اختيار فرع الباقة: مخصصة. أما العلمي والأدبي والتاسع فيتم حساب موادها تلقائياً."
        self.fields["notes"].required = False

    def save(self, commit=True):
        package = super().save(commit=False)
        price_amount = self.cleaned_data.get("price_amount")
        package.price_cents = int(price_amount * 100) if price_amount is not None else None
        if commit:
            package.save()
            if package.package_track == "custom":
                self.save_m2m()
            else:
                tracks = [package.package_track]
                if package.package_track in {"scientific", "literary"} and package.auto_include_shared:
                    tracks.append("general")
                package.courses.set(Course.objects.filter(academic_track__in=tracks, status="published"))
        return package


class PackageCodeGenerateForm(forms.Form):
    package = forms.ModelChoiceField(label="الباقة", queryset=CoursePackage.objects.filter(is_active=True).order_by("name"))
    quantity = forms.IntegerField(label="عدد الأكواد", min_value=1, initial=10)
    code_prefix = forms.CharField(label="بادئة الكود", max_length=24, required=False)


class PackageCodeSaleForm(forms.Form):
    code = forms.ModelChoiceField(label="كود الباقة", queryset=AccessCode.objects.none())
    student_name = forms.CharField(label="اسم الطالب", max_length=160)
    student_phone = forms.CharField(label="رقم الطالب", max_length=40)
    price_amount = forms.DecimalField(label="قيمة البيع", min_value=0, decimal_places=0, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["code"].queryset = (
            AccessCode.objects.filter(access_type="package", status="active", sale_status__in=["available", "reserved"])
            .select_related("package")
            .order_by("package__name", "created_at")
        )
        self.fields["code"].label_from_instance = lambda code: f"{code.code} - {code.package.name if code.package else 'باقة'}"
        self.fields["price_amount"].required = False


class InstructorAddForm(forms.Form):
    first_name = forms.CharField(label="الاسم الأول")
    last_name = forms.CharField(label="الكنية")
    username = forms.CharField(label="اسم المستخدم (رقم الهاتف)")
    password = forms.CharField(label="كلمة المرور", widget=forms.PasswordInput())
    specialty = forms.CharField(label="التخصص", required=False)
    bio = forms.CharField(label="النبذة التعريفية", widget=forms.Textarea(attrs={"rows": 3}), required=False)
    photo = forms.ImageField(label="الصورة الشخصية", required=False)


class InstructorEditForm(forms.Form):
    first_name = forms.CharField(label="الاسم الأول", max_length=120, required=False)
    last_name = forms.CharField(label="الكنية", max_length=120, required=False)
    username = forms.CharField(label="اسم المستخدم / الهاتف", max_length=150)
    specialty = forms.CharField(label="التخصص", max_length=120, required=False)
    bio = forms.CharField(label="النبذة التعريفية", widget=forms.Textarea(attrs={"rows": 3}), required=False)
    avatar = forms.ImageField(label="الصورة الشخصية", required=False)
    status = forms.ChoiceField(label="الحالة", choices=InstructorProfile.STATUS_CHOICES)

    def __init__(self, *args, instructor=None, **kwargs):
        self.instructor = instructor
        initial = kwargs.pop("initial", {})
        if instructor is not None:
            profile = instructor.instructor_profile
            initial = {
                **initial,
                "first_name": instructor.first_name,
                "last_name": instructor.last_name,
                "username": instructor.username,
                "specialty": profile.specialty,
                "bio": profile.bio,
                "status": profile.status,
            }
        super().__init__(*args, initial=initial, **kwargs)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        qs = User.objects.filter(username=username)
        if self.instructor is not None:
            qs = qs.exclude(id=self.instructor.id)
        if qs.exists():
            raise ValidationError("اسم المستخدم / الهاتف مستخدم مسبقاً.")
        return username

    def save(self):
        instructor = self.instructor
        profile = instructor.instructor_profile
        instructor.first_name = self.cleaned_data["first_name"].strip()
        instructor.last_name = self.cleaned_data["last_name"].strip()
        instructor.username = self.cleaned_data["username"]
        instructor.is_staff = True
        instructor.save(update_fields=["first_name", "last_name", "username", "is_staff"])
        profile.specialty = self.cleaned_data["specialty"].strip()
        profile.bio = self.cleaned_data["bio"].strip()
        profile.status = self.cleaned_data["status"]
        if self.cleaned_data.get("avatar"):
            profile.avatar = self.cleaned_data["avatar"]
        profile.save()
        return instructor


class PartnerInstituteImportForm(forms.Form):
    course = forms.ModelChoiceField(label="الدورة", queryset=Course.objects.select_related("subject", "instructor").order_by("-created_at"))
    batch_name = forms.CharField(label="اسم دفعة الطلاب", max_length=160)
    file = forms.FileField(label="ملف الطلاب Excel/CSV")
    code_prefix = forms.CharField(label="بادئة الكود", max_length=24, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].label_from_instance = _course_display_label


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["name", "slug", "description"]
        labels = {
            "name": "اسم المادة",
            "slug": "الرابط المختصر (Slug)",
            "description": "وصف المادة",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = False
        self.fields["slug"].required = False
        self.fields["slug"].help_text = "اتركه فارغاً ليتم توليده تلقائياً"


class CatalogSectionForm(forms.ModelForm):
    class Meta:
        model = CatalogSection
        fields = ["label", "kind", "track", "sort_order", "is_visible"]
        labels = {
            "label": "اسم الفلتر",
            "kind": "نوع المحتوى",
            "track": "الفرع",
            "sort_order": "الترتيب",
            "is_visible": "ظاهر للطلاب",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kind"].widget = forms.Select(choices=Course.KIND_CHOICES)
        self.fields["track"].widget = forms.Select(choices=Course.TRACK_CHOICES)


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ["course", "title", "description", "sort_order"]
        labels = {
            "course": "الدورة التابعة",
            "title": "اسم الوحدة",
            "description": "وصف الوحدة",
            "sort_order": "الترتيب",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = False


class AcademicBranchForm(forms.ModelForm):
    class Meta:
        model = AcademicBranch
        fields = ["name", "sort_order", "is_active"]
        labels = {
            "name": "اسم الفرع / القسم",
            "sort_order": "الترتيب",
            "is_active": "نشط",
        }
