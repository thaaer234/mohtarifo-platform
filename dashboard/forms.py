from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.text import slugify

from accounts.models import AcademicBranch, Governorate
from billing.models import AccessCodeBatch, Institute, SalesCenter
from learning.models import Course, Lesson, Subject, Unit


class StudentRegistrationForm(UserCreationForm):
    first_name = forms.CharField(label="الاسم الكامل", max_length=120)
    username = forms.CharField(label="رقم الهاتف", max_length=40)
    track = forms.ChoiceField(label="الفرع", choices=[])
    governorate = forms.ChoiceField(label="المحافظة", choices=[])
    email = forms.EmailField(label="البريد الإلكتروني", required=False)

    class Meta:
        model = User
        fields = ["first_name", "username", "track", "governorate", "email", "password1", "password2"]
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
        self.fields["track"].choices = branch_choices
        self.fields["governorate"].choices = governorate_choices

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
            "title",
            "description",
            "price_amount",
            "teacher_photo",
            "cover",
            "status",
        ]
        labels = {
            "kind": "نوع المحتوى",
            "academic_track": "الفرع",
            "term": "الفصل",
            "instructor": "الأستاذ",
            "title": "اسم المكثفة أو الدورة",
            "description": "وصف مختصر",
            "teacher_photo": "صورة المدرس",
            "cover": "غلاف اختياري",
            "status": "حالة النشر",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["instructor"].queryset = User.objects.filter(is_staff=True).order_by("first_name", "username")
        self.fields["description"].required = False
        self.fields["cover"].required = False
        self.fields["teacher_photo"].required = False
        self.fields["status"].initial = "draft"

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("subject") and not cleaned.get("new_subject"):
            raise forms.ValidationError("اختر مادة موجودة أو اكتب مادة جديدة.")
        return cleaned

    def save(self, commit=True):
        course = super().save(commit=False)
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
        fields = ["unit", "title", "description", "video_url", "video_file", "duration_seconds", "sort_order"]
        labels = {
            "unit": "الوحدة / الجلسة",
            "title": "عنوان القسم",
            "description": "وصف مختصر",
            "video_url": "رابط Bunny.net (أو رابط خارجي)",
            "video_file": "أو رفع ملف فيديو محمي",
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
        if course is not None:
            self.fields["unit"].queryset = course.units.order_by("sort_order", "id")

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("video_file") and not cleaned.get("video_url"):
            raise forms.ValidationError("يجب إدخال رابط فيديو أو رفع ملف.")
        return cleaned


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
    course = forms.ModelChoiceField(label="الدورة", queryset=Course.objects.order_by("-created_at"))
    name = forms.CharField(label="اسم الدفعة", max_length=160)
    quantity = forms.IntegerField(label="عدد الأكواد", min_value=0, initial=0)
    code_prefix = forms.CharField(label="بادئة الكود", max_length=24, required=False)
    notes = forms.CharField(label="ملاحظات", required=False, widget=forms.Textarea(attrs={"rows": 3}))


class InstructorAddForm(forms.Form):
    first_name = forms.CharField(label="الاسم الأول")
    last_name = forms.CharField(label="الكنية")
    username = forms.CharField(label="اسم المستخدم (رقم الهاتف)")
    password = forms.CharField(label="كلمة المرور", widget=forms.PasswordInput())
    specialty = forms.CharField(label="التخصص", required=False)
    bio = forms.CharField(label="النبذة التعريفية", widget=forms.Textarea(attrs={"rows": 3}), required=False)
    photo = forms.ImageField(label="الصورة الشخصية", required=False)


class PartnerInstituteImportForm(forms.Form):
    course = forms.ModelChoiceField(label="الدورة", queryset=Course.objects.order_by("-created_at"))
    batch_name = forms.CharField(label="اسم دفعة الطلاب", max_length=160)
    file = forms.FileField(label="ملف الطلاب Excel/CSV")
    code_prefix = forms.CharField(label="بادئة الكود", max_length=24, required=False)


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
