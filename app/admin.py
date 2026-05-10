from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import (MCQ, Chapter, Course, ExamAttempt, Lesson, Payment,
                     Subject, SubLesson, TransactionVerification,
                     UserCourseEnrollment, UserMasterProgress, UserProfile)

# ──────────────────────────────────────────────
# Inlines
# ──────────────────────────────────────────────

class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    show_change_link = True


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    show_change_link = True


class SubLessonInline(admin.TabularInline):
    model = SubLesson
    extra = 0
    readonly_fields = ("mcq_count",)
    show_change_link = True


class MCQInline(admin.TabularInline):
    model = MCQ
    extra = 0
    fields = ("question", "correct_answer", "subject", "chapter", "lesson", "sub_lesson")
    show_change_link = True


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("user", "course", "payment_system", "month", "transaction_id", "amount", "status", "created_at")
    can_delete = False
    show_change_link = True


# ──────────────────────────────────────────────
# Subject
# ──────────────────────────────────────────────

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "chapter_count", "mcq_count")
    search_fields = ("name",)
    inlines = [ChapterInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _chapter_count=Count("chapters", distinct=True),
            _mcq_count=Count("mcqs", distinct=True),
        )

    @admin.display(description="Chapters", ordering="_chapter_count")
    def chapter_count(self, obj):
        return obj._chapter_count

    @admin.display(description="MCQs", ordering="_mcq_count")
    def mcq_count(self, obj):
        return obj._mcq_count


# ──────────────────────────────────────────────
# Chapter
# ──────────────────────────────────────────────

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "subject", "lesson_count")
    list_filter = ("subject",)
    search_fields = ("name", "subject__name")
    autocomplete_fields = ("subject",)
    inlines = [LessonInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_lesson_count=Count("lessons", distinct=True))

    @admin.display(description="Lessons", ordering="_lesson_count")
    def lesson_count(self, obj):
        return obj._lesson_count


# ──────────────────────────────────────────────
# Lesson
# ──────────────────────────────────────────────

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "chapter", "get_subject", "sub_lesson_count")
    list_filter = ("chapter__subject", "chapter")
    search_fields = ("name", "chapter__name", "chapter__subject__name")
    autocomplete_fields = ("chapter",)
    inlines = [SubLessonInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("chapter__subject").annotate(
            _sub_lesson_count=Count("sub_lessons", distinct=True)
        )

    @admin.display(description="Subject")
    def get_subject(self, obj):
        return obj.chapter.subject if obj.chapter else "—"

    @admin.display(description="Sub-Lessons", ordering="_sub_lesson_count")
    def sub_lesson_count(self, obj):
        return obj._sub_lesson_count


# ──────────────────────────────────────────────
# SubLesson
# ──────────────────────────────────────────────

@admin.register(SubLesson)
class SubLessonAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "lesson", "get_chapter", "get_subject", "mcq_count")
    list_filter = ("lesson__chapter__subject", "lesson__chapter")
    search_fields = ("name", "lesson__name", "lesson__chapter__name")
    autocomplete_fields = ("lesson",)
    readonly_fields = ("mcq_count",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "lesson__chapter__subject"
        )

    @admin.display(description="Chapter")
    def get_chapter(self, obj):
        return obj.lesson.chapter if obj.lesson else "—"

    @admin.display(description="Subject")
    def get_subject(self, obj):
        if obj.lesson and obj.lesson.chapter:
            return obj.lesson.chapter.subject
        return "—"


# ──────────────────────────────────────────────
# MCQ
# ──────────────────────────────────────────────

@admin.register(MCQ)
class MCQAdmin(admin.ModelAdmin):
    list_display = ("id", "short_question", "subject", "chapter", "lesson", "sub_lesson", "correct_answer")
    list_filter = ("subject", "chapter", "lesson")
    search_fields = ("question", "subject__name", "chapter__name", "lesson__name")
    autocomplete_fields = ("subject", "chapter", "lesson", "sub_lesson")
    fieldsets = (
        ("Hierarchy", {
            "fields": ("subject", "chapter", "lesson", "sub_lesson")
        }),
        ("Question", {
            "fields": ("question", "option_1", "option_2", "option_3", "option_4", "correct_answer")
        }),
        ("Extra", {
            "fields": ("explanation", "previous_year"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Question")
    def short_question(self, obj):
        return obj.question[:60] + ("…" if len(obj.question) > 60 else "")


# ──────────────────────────────────────────────
# Course
# ──────────────────────────────────────────────

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "total_subjects", "total_questions",
                    "one_month_price", "six_month_price", "one_year_price",
                    "created_at")
    search_fields = ("name",)
    filter_horizontal = ("subjects",)
    readonly_fields = ("total_subjects", "total_questions", "created_at", "updated_at")
    fieldsets = (
        (None, {
            "fields": ("name", "description", "image", "subjects")
        }),
        ("Pricing", {
            "fields": ("one_month_price", "six_month_price", "one_year_price")
        }),
        ("Stats (auto-updated)", {
            "fields": ("total_subjects", "total_questions", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


# ──────────────────────────────────────────────
# UserCourseEnrollment
# ──────────────────────────────────────────────

@admin.register(UserCourseEnrollment)
class UserCourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "course", "status", "start_time", "end_time", "enrolled_at", "is_expired")
    list_filter = ("status", "course")
    search_fields = ("user__username", "course__name")
    readonly_fields = ("enrolled_at",)
    autocomplete_fields = ("user", "course")

    @admin.display(description="Expired?", boolean=True)
    def is_expired(self, obj):
        return obj.is_expired()


# ──────────────────────────────────────────────
# ExamAttempt
# ──────────────────────────────────────────────

@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "subject", "exam_date",
        "total_questions", "correct_answers", "wrong_answers",
        "skipped_answers", "score_percentage"
    )
    list_filter = ("subject", "exam_date")
    search_fields = ("user__username", "subject__name")
    readonly_fields = (
        "user", "subject", "exam_date",
        "total_questions", "correct_answers", "wrong_answers",
        "skipped_answers", "score_percentage",
        "mcq_ids_order", "user_answers", "correct_status",
        "selected_chapters", "selected_sub_lessons",
    )

    def has_add_permission(self, request):
        return False  # Exam attempts are created by the app, not manually


# ──────────────────────────────────────────────
# UserMasterProgress
# ──────────────────────────────────────────────

@admin.register(UserMasterProgress)
class UserMasterProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "total_sub_lessons", "total_questions_answered", "total_correct_answers", "last_updated")
    search_fields = ("user__username",)
    readonly_fields = (
        "user", "total_sub_lessons", "total_questions_answered",
        "total_correct_answers", "last_updated", "created_at", "progress_data"
    )

    def has_add_permission(self, request):
        return False


# ──────────────────────────────────────────────
# TransactionVerification
# ──────────────────────────────────────────────

@admin.register(TransactionVerification)
class TransactionVerificationAdmin(admin.ModelAdmin):
    list_display = ("id", "payment_system", "transaction_id", "amount", "is_complete", "created_at")
    list_filter = ("payment_system", "is_complete")
    search_fields = ("transaction_id",)
    readonly_fields = ("is_complete", "created_at")
    inlines = [PaymentInline]

    fieldsets = (
        (None, {
            "fields": ("payment_system", "transaction_id", "amount")
        }),
        ("Status", {
            "fields": ("is_complete", "created_at"),
        }),
    )


# ──────────────────────────────────────────────
# Payment
# ──────────────────────────────────────────────

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "course", "payment_system",
        "transaction_id", "amount", "month", "status_badge", "created_at"
    )
    list_filter = ("status", "payment_system", "month", "course")
    search_fields = ("user__username", "transaction_id", "course__name")
    readonly_fields = ("created_at", "verified_transaction")
    autocomplete_fields = ("user", "course")

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "approved": "green",
            "pending": "orange",
            "rejected": "red",
        }
        color = colors.get(obj.status, "grey")
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            color,
            obj.get_status_display(),
        )


# ──────────────────────────────────────────────
# UserProfile
# ──────────────────────────────────────────────

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "phone_number", "district", "created_at")
    search_fields = ("user__username", "user__first_name", "user__last_name", "phone_number", "district")
    readonly_fields = ("created_at", "updated_at", "profile_image_preview")

    def profile_image_preview(self, obj):
        if obj.profile_image:
            return format_html('<img src="{}" width="80" style="border-radius:50%;" />', obj.profile_image.url)
        return "No image"
    profile_image_preview.short_description = "Preview"

    fieldsets = (
        (None, {
            "fields": ("user", "profile_image", "profile_image_preview")
        }),
        ("Details", {
            "fields": ("phone_number", "district", "bio")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )