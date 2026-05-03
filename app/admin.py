# admin.py
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.db.models import Count
from django.shortcuts import redirect
from .models import (
    Subject, Chapter, Lesson, SubLesson, MCQ, ExamAttempt, 
    Course, UserCourseEnrollment, Payment, TransactionVerification
)

# ===========================================
# PAYMENT & TRANSACTION ADMIN (Unchanged)
# ===========================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "id", "user", "course", "payment_system", "month", 
        "amount", "transaction_id", "status", "verified_transaction", "created_at",
    ]
    list_filter = ["payment_system", "status", "month", "created_at"]
    search_fields = ["user__username", "course__name", "transaction_id"]
    readonly_fields = ["created_at", "amount"]
    list_per_page = 25


@admin.register(TransactionVerification)
class TransactionVerificationAdmin(admin.ModelAdmin):
    list_display = ['is_complete', "id", "payment_system", "transaction_id", "amount", "created_at"]
    list_filter = ["payment_system", "created_at"]
    search_fields = ["transaction_id"]
    readonly_fields = ["created_at"]
    list_per_page = 25


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'total_subjects', 'total_questions', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name']
    filter_horizontal = ['subjects']


@admin.register(UserCourseEnrollment)
class UserCourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'course', 'status', 'start_time', 'end_time', 'enrolled_at']
    list_filter = ['status', 'course']
    search_fields = ['user__username', 'course__name']


# ===========================================
# OPTIMIZED INLINES (NO NESTED INLINES)
# ===========================================

class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    show_change_link = True
    fields = ['name']
    max_num = 0


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    show_change_link = True
    fields = ['name']
    max_num = 0


class SubLessonInline(admin.TabularInline):
    model = SubLesson
    extra = 0
    show_change_link = True
    fields = ['name']
    max_num = 0


class MCQInline(admin.TabularInline):
    model = MCQ
    extra = 0
    show_change_link = True
    fields = ['question_short', 'correct_answer']
    max_num = 0
    readonly_fields = ['question_short']
    
    def question_short(self, obj):
        return obj.question[:50] if obj.question else ''
    question_short.short_description = "Question Preview"


# ===========================================
# SUBJECT ADMIN
# ===========================================

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'total_chapters', 'total_mcqs', 'view_details_link']
    search_fields = ['name']
    inlines = [ChapterInline]
    readonly_fields = ['total_chapters', 'total_mcqs']
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            chapter_count=Count('chapters', distinct=True),
            mcq_count=Count('chapters__lessons__sub_lessons__mcqs', distinct=True)
        )
    
    def total_chapters(self, obj):
        return obj.chapter_count
    total_chapters.admin_order_field = 'chapter_count'
    total_chapters.short_description = 'Total Chapters'
    
    def total_mcqs(self, obj):
        return obj.mcq_count
    total_mcqs.admin_order_field = 'mcq_count'
    total_mcqs.short_description = 'Total MCQs'
    
    def view_details_link(self, obj):
        url = reverse('admin:app_chapter_changelist') + f'?subject__id__exact={obj.id}'
        return format_html('<a href="{}">View Chapters →</a>', url)
    view_details_link.short_description = 'Details'


# ===========================================
# CHAPTER ADMIN
# ===========================================

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'subject', 'total_lessons', 'total_mcqs', 'view_lessons_link']
    list_filter = ['subject']
    search_fields = ['name']
    inlines = [LessonInline]
    list_select_related = ['subject']
    readonly_fields = ['total_lessons', 'total_mcqs']
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            lesson_count=Count('lessons', distinct=True),
            mcq_count=Count('lessons__sub_lessons__mcqs', distinct=True)
        )
    
    def total_lessons(self, obj):
        return obj.lesson_count
    total_lessons.admin_order_field = 'lesson_count'
    total_lessons.short_description = 'Lessons'
    
    def total_mcqs(self, obj):
        return obj.mcq_count
    total_mcqs.admin_order_field = 'mcq_count'
    total_mcqs.short_description = 'MCQs'
    
    def view_lessons_link(self, obj):
        url = reverse('admin:app_lesson_changelist') + f'?chapter__id__exact={obj.id}'
        return format_html('<a href="{}">View Lessons ({})</a>', url, obj.lesson_count)
    view_lessons_link.short_description = 'Lessons'


# ===========================================
# LESSON ADMIN
# ===========================================

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'chapter', 'total_sub_lessons', 'total_mcqs', 'view_sub_lessons_link']
    list_filter = ['chapter__subject', 'chapter']
    search_fields = ['name']
    inlines = [SubLessonInline]
    list_select_related = ['chapter', 'chapter__subject']
    readonly_fields = ['total_sub_lessons', 'total_mcqs']
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            sublesson_count=Count('sub_lessons', distinct=True),
            mcq_count=Count('sub_lessons__mcqs', distinct=True)
        )
    
    def total_sub_lessons(self, obj):
        return obj.sublesson_count
    total_sub_lessons.admin_order_field = 'sublesson_count'
    total_sub_lessons.short_description = 'Sub-Lessons'
    
    def total_mcqs(self, obj):
        return obj.mcq_count
    total_mcqs.admin_order_field = 'mcq_count'
    total_mcqs.short_description = 'Total MCQs'
    
    def view_sub_lessons_link(self, obj):
        url = reverse('admin:app_sublesson_changelist') + f'?lesson__id__exact={obj.id}'
        return format_html('<a href="{}">View Sub-Lessons ({})</a>', url, obj.sublesson_count)
    view_sub_lessons_link.short_description = 'Sub-Lessons'


# ===========================================
# SUBLESSON ADMIN (WITH GLOBAL RECALCULATE BUTTON)
# ===========================================

@admin.register(SubLesson)
class SubLessonAdmin(admin.ModelAdmin):
    change_list_template = 'admin/sublesson_changelist.html'  # Custom template for button
    list_display = ['id', 'name', 'lesson', 'mcq_count', 'actual_count_display', 'fix_individual_button']
    list_filter = ['lesson__chapter__subject']
    search_fields = ['name']
    list_select_related = ['lesson__chapter__subject']
    actions = ['fix_selected_counts']
    
    def get_queryset(self, request):
        """Add actual count annotation"""
        queryset = super().get_queryset(request)
        return queryset.annotate(actual_count=Count('mcqs'))
    
    def actual_count_display(self, obj):
        """Show actual count with warning if mismatch"""
        if hasattr(obj, 'actual_count'):
            if obj.mcq_count != obj.actual_count:
                return format_html(
                    '<span style="color: #DC2626; font-weight: bold;">{} ⚠️</span>',
                    obj.actual_count
                )
            return format_html(
                '<span style="color: #10B981; font-weight: bold;">{} ✓</span>',
                obj.actual_count
            )
        return obj.mcqs.count()
    actual_count_display.short_description = 'Actual Count'
    
    def fix_individual_button(self, obj):
        """Individual fix button for each row"""
        from django.urls import reverse
        from django.utils.html import format_html
        
        url = reverse('admin:app_sublesson_changelist') + f'?fix_id={obj.id}'
        return format_html(
            '<a class="button" href="{}" style="background: #3B82F6; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; font-size: 11px;">🔧 Fix</a>',
            url
        )
    fix_individual_button.short_description = 'Fix'
    fix_individual_button.allow_tags = True
    
    def changelist_view(self, request, extra_context=None):
        """Handle global recalculate and individual fix actions"""
        
        # Handle global recalculate all
        if request.GET.get('recalculate_all'):
            sub_lessons = SubLesson.objects.all()
            updated = 0
            total = 0
            
            for sub in sub_lessons:
                total += 1
                actual = sub.mcqs.count()
                if sub.mcq_count != actual:
                    sub.mcq_count = actual
                    sub.save(update_fields=['mcq_count'])
                    updated += 1
            
            self.message_user(
                request,
                f'✅ Global Recalculation Complete! Fixed {updated} out of {total} sub-lessons.',
                level='SUCCESS'
            )
            return redirect(reverse('admin:app_sublesson_changelist'))
        
        # Handle individual fix
        if request.GET.get('fix_id'):
            sub_id = request.GET.get('fix_id')
            try:
                sub = SubLesson.objects.get(id=sub_id)
                old = sub.mcq_count
                new = sub.mcqs.count()
                if old != new:
                    sub.mcq_count = new
                    sub.save(update_fields=['mcq_count'])
                    self.message_user(
                        request,
                        f'✅ Fixed "{sub.name}": {old} → {new} MCQs',
                        level='SUCCESS'
                    )
                else:
                    self.message_user(
                        request,
                        f'✓ "{sub.name}" count is already correct ({new} MCQs)',
                        level='INFO'
                    )
            except SubLesson.DoesNotExist:
                self.message_user(request, '❌ Sub-lesson not found', level='ERROR')
            
            return redirect(reverse('admin:app_sublesson_changelist'))
        
        return super().changelist_view(request, extra_context)
    
    def fix_selected_counts(self, request, queryset):
        """Admin action to fix selected sub-lessons"""
        updated = 0
        for sub in queryset:
            old = sub.mcq_count
            new = sub.mcqs.count()
            if old != new:
                sub.mcq_count = new
                sub.save(update_fields=['mcq_count'])
                updated += 1
        
        if updated > 0:
            self.message_user(
                request,
                f'✅ Fixed {updated} sub-lesson(s)!',
                level='SUCCESS'
            )
        else:
            self.message_user(
                request,
                '✓ All selected sub-lessons already have correct counts!',
                level='INFO'
            )
    fix_selected_counts.short_description = "Fix MCQ counts for selected"


# ===========================================
# MCQ ADMIN
# ===========================================

@admin.register(MCQ)
class MCQAdmin(admin.ModelAdmin):
    list_display = ['id', 'question_preview', 'sub_lesson_link', 'correct_answer', 'has_explanation']
    list_filter = ['sub_lesson__lesson__chapter__subject', 'sub_lesson__lesson__chapter', 'sub_lesson']
    search_fields = ['question', 'explanation']
    raw_id_fields = ['sub_lesson']
    list_per_page = 50
    list_select_related = ['sub_lesson__lesson__chapter__subject']
    
    fieldsets = (
        (None, {
            'fields': ('sub_lesson', 'question', ('option_1', 'option_2', 'option_3', 'option_4'), 'correct_answer')
        }),
        ('Explanation', {
            'fields': ('explanation',),
            'classes': ('collapse',)
        }),
    )
    
    def question_preview(self, obj):
        return obj.question[:100] + '...' if len(obj.question) > 100 else obj.question
    question_preview.short_description = 'Question'
    question_preview.admin_order_field = 'question'
    
    def sub_lesson_link(self, obj):
        url = reverse('admin:app_sublesson_change', args=[obj.sub_lesson.id])
        return format_html('<a href="{}">{}</a>', url, obj.sub_lesson.name)
    sub_lesson_link.short_description = 'Sub-Lesson'
    sub_lesson_link.admin_order_field = 'sub_lesson__name'
    
    def has_explanation(self, obj):
        return bool(obj.explanation)
    has_explanation.boolean = True
    has_explanation.short_description = 'Has Explanation'
    
    actions = ['delete_selected', 'export_as_csv']
    
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="mcqs_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Question', 'Option 1', 'Option 2', 'Option 3', 'Option 4', 'Correct Answer', 'Explanation', 'Sub-Lesson'])
        
        for mcq in queryset:
            writer.writerow([
                mcq.id, mcq.question, mcq.option_1, mcq.option_2, 
                mcq.option_3, mcq.option_4, mcq.correct_answer, 
                mcq.explanation, mcq.sub_lesson.name
            ])
        
        return response
    export_as_csv.short_description = "Export selected MCQs to CSV"


# ===========================================
# EXAM ATTEMPT ADMIN
# ===========================================

@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'subject', 'score_percentage', 'total_questions', 'correct_answers', 'exam_date']
    list_filter = ['subject', 'exam_date']
    search_fields = ['user__username', 'subject__name']
    readonly_fields = ['exam_date']
    list_per_page = 50
    
from app.models import UserMasterProgress,UserProfile
admin.site.register(UserMasterProgress)
admin.site.register(UserProfile)