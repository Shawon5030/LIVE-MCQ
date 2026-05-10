import json
import random
from datetime import datetime
from io import BytesIO

from django.contrib import messages
# Admin views for payment verification
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import (require_GET, require_http_methods,
                                          require_POST)
from xhtml2pdf import pisa

from app.models import UserCourseEnrollment

from .models import (MCQ, Chapter, Course, ExamAttempt, Lesson, Payment,
                     Subject, SubLesson, TransactionVerification, User,
                     UserCourseEnrollment, UserMasterProgress, UserProfile)


def Home_page(request):
    return render(request,'index.html')
def Contact_page(request):
    return render(request,'contact.html')
def Features_page(request):
    return render(request,'features.html')
def Faq_page(request):
    return render(request,'faq.html')



# views.py - Complete with all API functions


# ---------- PAGE VIEW ----------
def upload_mcq_page(request):
    """Render the Tailwind HTML page for MCQ upload."""
    return render(request, 'upload.html')


# ---------- API ENDPOINTS (with /upload/ suffix as per your URLs) ----------
@require_http_methods(["GET"])
def api_subjects(request):
    """Return list of all subjects."""
    subjects = Subject.objects.all().values('id', 'name')
    return JsonResponse(list(subjects), safe=False)


@require_http_methods(["GET"])
def api_chapters(request):
    """Return chapters for a given subject_id (GET param)."""
    subject_id = request.GET.get('subject_id')
    if not subject_id:
        return JsonResponse([], safe=False)
    chapters = Chapter.objects.filter(subject_id=subject_id).values('id', 'name')
    return JsonResponse(list(chapters), safe=False)


@require_http_methods(["GET"])
def api_lessons(request):
    """Return lessons for a given chapter_id (GET param)."""
    chapter_id = request.GET.get('chapter_id')
    if not chapter_id:
        return JsonResponse([], safe=False)
    lessons = Lesson.objects.filter(chapter_id=chapter_id).values('id', 'name')
    return JsonResponse(list(lessons), safe=False)


@require_http_methods(["GET"])
def api_sub_lessons(request):
    """Return sub-lessons for a given lesson_id (GET param)."""
    lesson_id = request.GET.get('lesson_id')
    if not lesson_id:
        return JsonResponse([], safe=False)
    sub_lessons = SubLesson.objects.filter(lesson_id=lesson_id).values('id', 'name')
    return JsonResponse(list(sub_lessons), safe=False)


@csrf_exempt
@require_http_methods(["POST"])
def api_bulk_upload_mcq(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    mcq_list = data.get("mcqs")
    if not isinstance(mcq_list, list):
        return JsonResponse({"error": "'mcqs' must be an array"}, status=400)

    # Get defaults (should be integers or None)
    defaults = data.get("defaults", {})
    default_subject_id = defaults.get("subject_id")
    default_chapter_id = defaults.get("chapter_id")
    default_lesson_id = defaults.get("lesson_id")
    default_sub_lesson_id = defaults.get("sub_lesson_id")

    created_count = 0
    errors = []

    for idx, item in enumerate(mcq_list):
        try:
            # Merge item with defaults (item takes precedence if not None)
            sub_lesson_id = item.get("sub_lesson_id")
            if sub_lesson_id is None:
                sub_lesson_id = default_sub_lesson_id
            lesson_id = item.get("lesson_id")
            if lesson_id is None:
                lesson_id = default_lesson_id
            chapter_id = item.get("chapter_id")
            if chapter_id is None:
                chapter_id = default_chapter_id
            subject_id = item.get("subject_id")
            if subject_id is None:
                subject_id = default_subject_id

            # Extract MCQ fields
            question = item.get("question", "").strip()
            option_1 = item.get("option_1", "").strip()
            option_2 = item.get("option_2", "").strip()
            option_3 = item.get("option_3", "").strip()
            option_4 = item.get("option_4", "").strip()
            correct_answer = item.get("correct_answer")
            previous_year = item.get("previous_year") or None
            explanation = item.get("explanation") or None

            # Basic validation
            if not all([question, option_1, option_2, option_3, option_4]):
                errors.append(f"Row {idx+1}: Missing question or one of the options.")
                continue
            if correct_answer not in [1,2,3,4]:
                errors.append(f"Row {idx+1}: correct_answer must be 1-4.")
                continue

            # Resolve hierarchy
            final_subject = final_chapter = final_lesson = final_sub_lesson = None

            if sub_lesson_id:
                try:
                    sub_obj = SubLesson.objects.select_related('lesson__chapter__subject').get(id=sub_lesson_id)
                except SubLesson.DoesNotExist:
                    errors.append(f"Row {idx+1}: SubLesson id={sub_lesson_id} not found.")
                    continue
                final_sub_lesson = sub_obj
                final_lesson = sub_obj.lesson
                final_chapter = final_lesson.chapter
                final_subject = final_chapter.subject
                
                if lesson_id and lesson_id != final_lesson.id:
                    errors.append(f"Row {idx+1}: lesson_id mismatch with SubLesson.")
                    continue
                if chapter_id and chapter_id != final_chapter.id:
                    errors.append(f"Row {idx+1}: chapter_id mismatch with SubLesson.")
                    continue
                if subject_id and subject_id != final_subject.id:
                    errors.append(f"Row {idx+1}: subject_id mismatch with SubLesson.")
                    continue

            elif lesson_id:
                try:
                    lesson_obj = Lesson.objects.select_related('chapter__subject').get(id=lesson_id)
                except Lesson.DoesNotExist:
                    errors.append(f"Row {idx+1}: Lesson id={lesson_id} not found.")
                    continue
                final_lesson = lesson_obj
                final_chapter = lesson_obj.chapter
                final_subject = final_chapter.subject
                
                if chapter_id and chapter_id != final_chapter.id:
                    errors.append(f"Row {idx+1}: chapter_id mismatch with Lesson.")
                    continue
                if subject_id and subject_id != final_subject.id:
                    errors.append(f"Row {idx+1}: subject_id mismatch with Lesson.")
                    continue

            elif chapter_id:
                try:
                    chapter_obj = Chapter.objects.select_related('subject').get(id=chapter_id)
                except Chapter.DoesNotExist:
                    errors.append(f"Row {idx+1}: Chapter id={chapter_id} not found.")
                    continue
                final_chapter = chapter_obj
                final_subject = chapter_obj.subject
                
                if subject_id and subject_id != final_subject.id:
                    errors.append(f"Row {idx+1}: subject_id mismatch with Chapter.")
                    continue

            else:
                if not subject_id:
                    errors.append(f"Row {idx+1}: No subject_id provided (neither in item nor defaults).")
                    continue
                try:
                    final_subject = Subject.objects.get(id=subject_id)
                except Subject.DoesNotExist:
                    errors.append(f"Row {idx+1}: Subject id={subject_id} not found.")
                    continue

            # Create MCQ
            mcq = MCQ.objects.create(
                subject=final_subject,
                chapter=final_chapter,
                lesson=final_lesson,
                sub_lesson=final_sub_lesson,
                question=question,
                option_1=option_1,
                option_2=option_2,
                option_3=option_3,
                option_4=option_4,
                correct_answer=correct_answer,
                previous_year=previous_year,
                explanation=explanation,
            )
            
            if final_sub_lesson:
                final_sub_lesson.update_mcq_count()
                
            created_count += 1

        except Exception as e:
            errors.append(f"Row {idx+1}: Unexpected error - {str(e)}")

    return JsonResponse({
        "created": created_count,
        "errors": errors,
        "total_submitted": len(mcq_list)
    }, status=200 if created_count > 0 else 400)
    
    
def login_page(request):
    if request.user.is_authenticated:
        return redirect('exam_home')
    return render(request, 'exam/login.html')


def register_page(request):
    if request.user.is_authenticated:
        return redirect('exam_home')
    return render(request, 'exam/register.html')


@csrf_exempt
def login_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            remember_me = data.get('remember_me', False)
            
            user = authenticate(request, username=username, password=password)
            
            if not user and '@' in username:
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            
            if user is not None:
                login(request, user)
                if not remember_me:
                    request.session.set_expiry(0)
                else:
                    request.session.set_expiry(1209600)
                return JsonResponse({'success': True, 'message': 'লগইন সফল হয়েছে'})
            else:
                return JsonResponse({'success': False, 'message': 'ইউজারনেম বা পাসওয়ার্ড ভুল'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid method'}, status=405)


@csrf_exempt
def register_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            confirm_password = data.get('confirm_password')
            
            if password != confirm_password:
                return JsonResponse({'success': False, 'message': 'পাসওয়ার্ড মিলছে না'}, status=400)
            
            if len(password) < 6:
                return JsonResponse({'success': False, 'message': 'পাসওয়ার্ড কমপক্ষে ৬ অক্ষরের হতে হবে'}, status=400)
            
            if User.objects.filter(username=username).exists():
                return JsonResponse({'success': False, 'message': 'এই ইউজারনেম already exists'}, status=400)
            
            if User.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'message': 'এই ইমেইল already registered'}, status=400)
            
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            return JsonResponse({'success': True, 'message': 'রেজিস্ট্রেশন সফল হয়েছে'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid method'}, status=405)


def logout_api(request):
    logout(request)
    return redirect('login_page')




# ─────────────────────────────────────────────
# 1. Hierarchy loaders (cascading dropdowns)
# ─────────────────────────────────────────────
@login_required
def exam_home(request):
    enrollments = UserCourseEnrollment.objects.filter(
        user=request.user,
        status="active",
       
    ).select_related(
        'course'
    ).prefetch_related(
        'course__subjects'
    )


    subjects = Subject.objects.filter(
        courses__enrollments__in=enrollments
    ).distinct()

    total_subject = subjects.count()
    if total_subject==0:
        
        messages.error(
        request,
        "আপনার কোনো কোর্স অ্যাক্টিভ নেই"
    )
        return redirect("course_list_page")
    return render(request,"exam/home.html")


# ─────────────────────────────────────────────
# 1. Hierarchy loaders (cascading dropdowns)
# ─────────────────────────────────────────────

@login_required
@require_GET
def get_subjects(request):
    enrollments = UserCourseEnrollment.objects.filter(
        user=request.user,
        status="active",
    ).select_related(
        "course"
    ).prefetch_related(
        "course__subjects"
    )

    subjects = Subject.objects.filter(
        courses__enrollments__in=enrollments
    ).distinct().values(
        "id",
        "name"
    )

    return JsonResponse({
        "subjects": list(subjects)
    })


@login_required
@require_GET
def get_chapters(request):
    
    ids = _parse_ids(request.GET.get("subject_ids", ""))
    if not ids:
        return JsonResponse({"error": "subject_ids required"}, status=400)
    chapters = (
        Chapter.objects
        .filter(subject_id__in=ids)
        .select_related("subject")
        .values("id", "name", "subject_id", "subject__name")
        .order_by("subject__name", "name")
    )
    return JsonResponse({"chapters": list(chapters)})


@login_required
@require_GET
def get_lessons(request):

    ids = _parse_ids(request.GET.get("chapter_ids", ""))
    if not ids:
        return JsonResponse({"error": "chapter_ids required"}, status=400)
    lessons = (
        Lesson.objects
        .filter(chapter_id__in=ids)
        .select_related("chapter__subject")
        .values("id", "name", "chapter_id", "chapter__name", "chapter__subject__name")
        .order_by("chapter__name", "name")
    )
    return JsonResponse({"lessons": list(lessons)})


@login_required
@require_GET
def get_sublessons(request):

    ids = _parse_ids(request.GET.get("lesson_ids", ""))
    if not ids:
        return JsonResponse({"error": "lesson_ids required"}, status=400)
    subs = (
        SubLesson.objects
        .filter(lesson_id__in=ids)
        .select_related("lesson__chapter__subject")
        .values(
            "id", "name", "mcq_count",
            "lesson_id", "lesson__name",
            "lesson__chapter__name",
            "lesson__chapter__subject__name"
        )
        .order_by("lesson__name", "name")
    )
    return JsonResponse({"sub_lessons": list(subs)})




@login_required
@require_GET
def preview_mcq_count(request):
    qs = _build_mcq_queryset(request.GET)
    return JsonResponse({"available_mcq_count": qs.count()})


# ─────────────────────────────────────────────
# 3. Start / Submit exam
# ─────────────────────────────────────────────




@require_POST
def start_exam(request):
    
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    subject_ids    = body.get("subject_ids", [])
    chapter_ids    = body.get("chapter_ids", [])
    lesson_ids     = body.get("lesson_ids", [])
    sub_lesson_ids = body.get("sub_lesson_ids", [])
    question_count = int(body.get("question_count", 20))
    time_limit     = int(body.get("time_limit_minutes", 10))
    random_order   = bool(body.get("random_order", True))
    include_answers = body.get("include_answers", False)  # NEW: flag to include answers

    # Check if user is admin - only admins can export answers
    is_admin = request.user.is_staff
    include_answers = include_answers and is_admin  # Only include if admin requests it

    if not any([subject_ids, chapter_ids, lesson_ids, sub_lesson_ids]):
        return JsonResponse({"error": "Select at least one subject, chapter, lesson, or sub-lesson."}, status=400)

    if question_count < 1 or question_count > 200:
        return JsonResponse({"error": "question_count must be between 1 and 200."}, status=400)

    # Collect MCQs
    mcq_qs = _build_mcq_queryset_from_lists(
        subject_ids, chapter_ids, lesson_ids, sub_lesson_ids
    )

    total_available = mcq_qs.count()
    if total_available == 0:
        return JsonResponse({"error": "No MCQs found for the selected filters."}, status=404)

    # Clamp count
    question_count = min(question_count, total_available)

    # Include all fields including correct_answer, explanation, previous_year
    mcq_list = list(mcq_qs.values(
        "id", "question",
        "option_1", "option_2", "option_3", "option_4",
        "subject_id", "chapter_id", "lesson_id", "sub_lesson_id",
        "previous_year", "correct_answer", "explanation"  # Now including these
    ))

    if random_order:
        random.shuffle(mcq_list)

    selected = mcq_list[:question_count]
    mcq_ids_order = [m["id"] for m in selected]

    # Derive the primary subject for ExamAttempt
    primary_subject_id = (
        subject_ids[0] if subject_ids
        else (selected[0]["subject_id"] if selected else None)
    )

    # Only create ExamAttempt for actual exam sessions (not admin exports)
    attempt = None
    
        # Create ExamAttempt (results empty – filled on submit)
    attempt = ExamAttempt.objects.create(
            user=request.user,
            subject_id=primary_subject_id,
            time_limit_minutes=time_limit,
            total_questions=question_count,
            mcq_ids_order=mcq_ids_order,
            user_answers=[None] * question_count,
            correct_status=[None] * question_count,
            selected_chapters=chapter_ids,
            selected_sub_lessons=sub_lesson_ids,
        )

    # Build questions for response
    questions_for_client = []
    for idx, m in enumerate(selected):
        question_data = {
            "index":      idx,
            "id":         m["id"],
            "question":   m["question"],
            "options": [
                {"key": 1, "text": m["option_1"]},
                {"key": 2, "text": m["option_2"]},
                {"key": 3, "text": m["option_3"]},
                {"key": 4, "text": m["option_4"]},
            ],
        }
        
        # Include correct_answer, explanation, and previous_year ONLY for admin exports
        if include_answers:
            question_data["correct_answer"]  = m["correct_answer"]
            question_data["explanation"]     = m["explanation"] or None
            question_data["previous_year"]   = m["previous_year"] or None
            question_data["subject_id"]      = m["subject_id"]       # already there
            question_data["chapter_id"]      = m["chapter_id"]       # already there
            question_data["lesson_id"]       = m["lesson_id"]        # ADD THIS
            question_data["sub_lesson_id"]   = m["sub_lesson_id"]    # ADD THIS
        
        questions_for_client.append(question_data)

    response_data = {
        "total_questions":    question_count,
        "time_limit_minutes": time_limit,
        "questions":          questions_for_client,
    }
    
    # Only include attempt_id if this is a real exam (not admin export)
    if attempt:
        response_data["attempt_id"] = attempt.id
    
    # If this is an admin export, add metadata
    if include_answers:
        response_data["export_type"] = "admin_export"
        response_data["exported_by"] = request.user.username
        response_data["total_available"] = total_available
    
    return JsonResponse(response_data)


def _build_mcq_queryset_from_lists(subject_ids, chapter_ids, lesson_ids, sub_lesson_ids):
    """Helper function to build MCQ queryset from filters"""
    from .models import MCQ  # Import here to avoid circular imports
    
    qs = MCQ.objects.all()
    
    if subject_ids:
        qs = qs.filter(subject_id__in=subject_ids)
    if chapter_ids:
        qs = qs.filter(chapter_id__in=chapter_ids)
    if lesson_ids:
        qs = qs.filter(lesson_id__in=lesson_ids)
    if sub_lesson_ids:
        qs = qs.filter(sub_lesson_id__in=sub_lesson_ids)
    
    return qs


@login_required
@require_POST
def submit_exam(request):

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    attempt_id = body.get("attempt_id")
    user_answers = body.get("answers", [])

    try:
        attempt = ExamAttempt.objects.get(id=attempt_id, user=request.user)
    except ExamAttempt.DoesNotExist:
        return JsonResponse({"error": "Exam attempt not found."}, status=404)

    mcq_ids = attempt.mcq_ids_order
    if len(user_answers) != len(mcq_ids):
        return JsonResponse({"error": "Answer count does not match question count."}, status=400)

    # Fetch correct answers
    mcqs = MCQ.objects.filter(id__in=mcq_ids).values("id", "correct_answer", "explanation",
                                                       "option_1", "option_2", "option_3", "option_4")
    correct_map = {m["id"]: m for m in mcqs}

    correct_count = 0
    wrong_count   = 0
    skipped_count = 0
    correct_status = []
    result_details = []

    for idx, (mcq_id, answer) in enumerate(zip(mcq_ids, user_answers)):
        mcq_data = correct_map.get(mcq_id, {})
        correct_ans = mcq_data.get("correct_answer")

        if answer is None:
            skipped_count += 1
            status = "skipped"
        elif answer == correct_ans:
            correct_count += 1
            status = "correct"
        else:
            wrong_count += 1
            status = "wrong"

        correct_status.append(status)
        result_details.append({
            "index":          idx,
            "mcq_id":         mcq_id,
            "your_answer":    answer,
            "correct_answer": correct_ans,
            "status":         status,
            "explanation":    mcq_data.get("explanation") or "",
            "options": [
                {"key": 1, "text": mcq_data.get("option_1", "")},
                {"key": 2, "text": mcq_data.get("option_2", "")},
                {"key": 3, "text": mcq_data.get("option_3", "")},
                {"key": 4, "text": mcq_data.get("option_4", "")},
            ],
        })

    total = attempt.total_questions
    score_pct = round((correct_count / total * 100) if total > 0 else 0, 2)

    # Save results
    attempt.user_answers    = user_answers
    attempt.correct_status  = correct_status
    attempt.correct_answers = correct_count
    attempt.wrong_answers   = wrong_count
    attempt.skipped_answers = skipped_count
    attempt.score_percentage = score_pct
    attempt.save()

    return JsonResponse({
        "attempt_id":       attempt.id,
        "total_questions":  total,
        "correct_answers":  correct_count,
        "wrong_answers":    wrong_count,
        "skipped_answers":  skipped_count,
        "score_percentage": score_pct,
        "result_details":   result_details,
    })

def _parse_ids(raw: str):
    """Parse comma-separated integer IDs from a query string value."""
    if not raw:
        return []
    try:
        return [int(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError:
        return []


def _build_mcq_queryset(GET):
    return _build_mcq_queryset_from_lists(
        _parse_ids(GET.get("subject_ids", "")),
        _parse_ids(GET.get("chapter_ids", "")),
        _parse_ids(GET.get("lesson_ids", "")),
        _parse_ids(GET.get("sub_lesson_ids", "")),
    )


def _build_mcq_queryset_from_lists(subject_ids, chapter_ids, lesson_ids, sub_lesson_ids):
    
    from django.db.models import Q

    sub_lesson_ids = list(sub_lesson_ids or [])
    lesson_ids     = list(lesson_ids     or [])
    chapter_ids    = list(chapter_ids    or [])
    subject_ids    = list(subject_ids    or [])

    if not any([sub_lesson_ids, lesson_ids, chapter_ids, subject_ids]):
        return MCQ.objects.none()


    covered_subject_ids = set()
    if chapter_ids:
        from .models import Chapter
        covered = Chapter.objects.filter(id__in=chapter_ids).values_list('subject_id', flat=True)
        covered_subject_ids.update(covered)

    if lesson_ids:
        from .models import Lesson
        covered = Lesson.objects.filter(id__in=lesson_ids).values_list('chapter__subject_id', flat=True)
        covered_subject_ids.update(covered)

    if sub_lesson_ids:
        from .models import SubLesson
        covered = SubLesson.objects.filter(id__in=sub_lesson_ids).values_list('lesson__chapter__subject_id', flat=True)
        covered_subject_ids.update(covered)


    covered_chapter_ids = set()

    if lesson_ids:
        from .models import Lesson
        covered = Lesson.objects.filter(id__in=lesson_ids).values_list('chapter_id', flat=True)
        covered_chapter_ids.update(covered)

    if sub_lesson_ids:
        from .models import SubLesson
        covered = SubLesson.objects.filter(id__in=sub_lesson_ids).values_list('lesson__chapter_id', flat=True)
        covered_chapter_ids.update(covered)

    # --- And a lesson is covered if a sublesson under it was selected ---
    covered_lesson_ids = set()

    if sub_lesson_ids:
        from .models import SubLesson
        covered = SubLesson.objects.filter(id__in=sub_lesson_ids).values_list('lesson_id', flat=True)
        covered_lesson_ids.update(covered)

    # --- Build the final Q ---
    q = Q()

    # Sub-lessons: always include as-is
    if sub_lesson_ids:
        q |= Q(sub_lesson_id__in=sub_lesson_ids)

    # Lessons: only include if not already covered by a sublesson selection
    effective_lesson_ids = [lid for lid in lesson_ids if lid not in covered_lesson_ids]
    if effective_lesson_ids:
        q |= Q(lesson_id__in=effective_lesson_ids)

    # Chapters: only include if not already covered by a lesson/sublesson selection
    effective_chapter_ids = [cid for cid in chapter_ids if cid not in covered_chapter_ids]
    if effective_chapter_ids:
        q |= Q(chapter_id__in=effective_chapter_ids)

    # Subjects: only include as fallback when not covered by any finer selection
    effective_subject_ids = [sid for sid in subject_ids if sid not in covered_subject_ids]
    if effective_subject_ids:
        q |= Q(subject_id__in=effective_subject_ids)

    if not q:
        return MCQ.objects.none()

    return MCQ.objects.filter(q).distinct()
    




# views.py (additions)


@login_required
def practice_home(request):
    enrollments = UserCourseEnrollment.objects.filter(
        user=request.user,
        status="active",
       
    ).select_related(
        'course'
    ).prefetch_related(
        'course__subjects'
    )


    subjects = Subject.objects.filter(
        courses__enrollments__in=enrollments
    ).distinct()

    total_subject = subjects.count()
    if total_subject==0:
        
        messages.error(
        request,
        "আপনার কোনো কোর্স অ্যাক্টিভ নেই"
    )
        return redirect("course_list_page")
    return render(request, 'exam/practice.html')


@login_required
@require_GET
def practice_content(request):

    subject_id = request.GET.get('subject_id')
    chapter_id = request.GET.get('chapter_id')
    lesson_id = request.GET.get('lesson_id')

    # Level 0: No subject selected → list all subjects
    if not subject_id:
        subjects = Subject.objects.all().order_by('name')
        items = []
        for s in subjects:
            mcq_count = MCQ.objects.filter(subject_id=s.id).count()
            has_children = Chapter.objects.filter(subject_id=s.id).exists()
            items.append({
                'id': s.id,
                'name': s.name,
                'type': 'subject',
                'mcq_count': mcq_count,
                'has_children': has_children,
            })
        return JsonResponse({'type': 'subjects', 'items': items})

    # Level 1: Subject selected, no chapter selected
    if subject_id and not chapter_id:
        chapters = Chapter.objects.filter(subject_id=subject_id).order_by('name')
        if chapters.exists():
            items = []
            for ch in chapters:
                mcq_count = MCQ.objects.filter(chapter_id=ch.id).count()
                has_children = Lesson.objects.filter(chapter_id=ch.id).exists()
                items.append({
                    'id': ch.id,
                    'name': ch.name,
                    'type': 'chapter',
                    'mcq_count': mcq_count,
                    'has_children': has_children,
                })
            return JsonResponse({'type': 'chapters', 'items': items})
        else:
            # No chapters → practice directly at subject level
            subject = Subject.objects.get(id=subject_id)
            mcq_count = MCQ.objects.filter(subject_id=subject_id).count()
            return JsonResponse({
                'type': 'direct',
                'level_type': 'subject',
                'level_id': subject_id,
                'level_name': subject.name,
                'mcq_count': mcq_count,
            })

    # Level 2: Chapter selected, no lesson selected
    if chapter_id and not lesson_id:
        lessons = Lesson.objects.filter(chapter_id=chapter_id).order_by('name')
        if lessons.exists():
            items = []
            for ls in lessons:
                mcq_count = MCQ.objects.filter(lesson_id=ls.id).count()
                has_children = SubLesson.objects.filter(lesson_id=ls.id).exists()
                items.append({
                    'id': ls.id,
                    'name': ls.name,
                    'type': 'lesson',
                    'mcq_count': mcq_count,
                    'has_children': has_children,
                })
            return JsonResponse({'type': 'lessons', 'items': items})
        else:
            chapter = Chapter.objects.get(id=chapter_id)
            mcq_count = MCQ.objects.filter(chapter_id=chapter_id).count()
            return JsonResponse({
                'type': 'direct',
                'level_type': 'chapter',
                'level_id': chapter_id,
                'level_name': chapter.name,
                'mcq_count': mcq_count,
            })

    # Level 3: Lesson selected → show sublessons (if any)
    if lesson_id:
        sublessons = SubLesson.objects.filter(lesson_id=lesson_id).order_by('name')
        if sublessons.exists():
            items = []
            for sl in sublessons:
                mcq_count = sl.mcq_count  # denormalized field
                items.append({
                    'id': sl.id,
                    'name': sl.name,
                    'type': 'sublesson',
                    'mcq_count': mcq_count,
                    'has_children': False,
                })
            return JsonResponse({'type': 'sublessons', 'items': items})
        else:
            lesson = Lesson.objects.get(id=lesson_id)
            mcq_count = MCQ.objects.filter(lesson_id=lesson_id).count()
            return JsonResponse({
                'type': 'direct',
                'level_type': 'lesson',
                'level_id': lesson_id,
                'level_name': lesson.name,
                'mcq_count': mcq_count,
            })

    return JsonResponse({'error': 'Invalid parameters'}, status=400)


@login_required
@require_POST
def start_practice(request):

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    level_type = body.get('level_type')
    level_id = body.get('level_id')
    random_order = body.get('random_order', False)

    if not level_type or not level_id:
        return JsonResponse({'error': 'level_type and level_id required'}, status=400)

    # Build filter for MCQs
    filters = {}
    level_name = ''

    if level_type == 'subject':
        filters['subject_id'] = level_id
        filters['chapter__isnull'] = True
        filters['lesson__isnull'] = True
        filters['sub_lesson__isnull'] = True
        level_name = Subject.objects.get(id=level_id).name
    elif level_type == 'chapter':
        filters['chapter_id'] = level_id
        filters['lesson__isnull'] = True
        filters['sub_lesson__isnull'] = True
        level_name = Chapter.objects.get(id=level_id).name
    elif level_type == 'lesson':
        filters['lesson_id'] = level_id
        filters['sub_lesson__isnull'] = True
        level_name = Lesson.objects.get(id=level_id).name
    elif level_type == 'sublesson':
        filters['sub_lesson_id'] = level_id
        level_name = SubLesson.objects.get(id=level_id).name
    else:
        return JsonResponse({'error': 'Invalid level_type'}, status=400)

    mcqs = MCQ.objects.filter(**filters)
    total = mcqs.count()
    if total == 0:
        return JsonResponse({'error': 'No MCQs found for this level'}, status=404)

    # Build questions list
    questions = []
    for mcq in mcqs:
        questions.append({
            'id': mcq.id,
            'question': mcq.question,
            'options': [mcq.option_1, mcq.option_2, mcq.option_3, mcq.option_4],
            'correct': mcq.correct_answer,
            'explanation': mcq.explanation or 'No explanation available.'
        })

    level_key = f"{level_type}_{level_id}"
    saved_progress = None
    if not random_order:
        master_progress, _ = UserMasterProgress.objects.get_or_create(user=request.user)
        progress_data = master_progress.progress_data.get(level_key, {})
        if progress_data and not progress_data.get('is_completed', False):
            saved_progress = {
                'answers': progress_data.get('user_answers', [None] * total),
                'current_index': progress_data.get('current_index', 0),
                'questions_order': progress_data.get('questions_order', []),
            }

    # If saved progress exists, reorder questions to match saved order
    if saved_progress and saved_progress['questions_order']:
        order_ids = saved_progress['questions_order']
        if len(order_ids) == total:
            reordered = []
            for qid in order_ids:
                q = next((q for q in questions if q['id'] == qid), None)
                if q:
                    reordered.append(q)
            if len(reordered) == total:
                questions = reordered
        saved_answers = saved_progress['answers']
        saved_index = saved_progress['current_index']
    else:
        saved_answers = None
        saved_index = 0
        if random_order:
            random.shuffle(questions)

    response = {
        'questions': questions,
        'level_name': level_name,
        'level_key': level_key,
        'total': total,
        'random_order': random_order,
    }
    if saved_answers is not None:
        response['saved_answers'] = saved_answers
        response['saved_index'] = saved_index

    return JsonResponse(response)


@login_required
@require_POST
def save_practice_progress(request):
    """Save current practice session progress."""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    level_key = body.get('level_key')
    user_answers = body.get('user_answers', [])
    questions_order = body.get('questions_order', [])
    current_index = body.get('current_index', 0)
    random_order = body.get('random_order', True)
    level_name = body.get('level_name', '')

    if random_order:
        return JsonResponse({'error': 'Cannot save progress when random order is on'}, status=400)

    if not level_key:
        return JsonResponse({'error': 'level_key required'}, status=400)

    master_progress, _ = UserMasterProgress.objects.get_or_create(user=request.user)
    answered_count = len([a for a in user_answers if a is not None])
    total_questions = len(questions_order)
    is_completed = answered_count == total_questions

    master_progress.progress_data[level_key] = {
        'user_answers': user_answers,
        'questions_order': questions_order,
        'current_index': current_index,
        'level_name': level_name,
        'total_questions': total_questions,
        'answered_questions': answered_count,
        'last_updated': datetime.now().isoformat(),
        'is_completed': is_completed,
        'random_order': random_order,
    }
    master_progress.save()
    return JsonResponse({'success': True})


@login_required
@require_GET
def delete_practice_progress(request):
    """Delete progress for a specific level key."""
    level_key = request.GET.get('level_key')
    if not level_key:
        return JsonResponse({'error': 'level_key required'}, status=400)

    master_progress, _ = UserMasterProgress.objects.get_or_create(user=request.user)
    if level_key in master_progress.progress_data:
        del master_progress.progress_data[level_key]
        master_progress.save()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Not found'}, status=404)


@login_required
@require_GET
def practice_progress_list(request):
    """List all active (non‑completed) practice sessions for the user."""
    master_progress, _ = UserMasterProgress.objects.get_or_create(user=request.user)
    items = []
    for key, data in master_progress.progress_data.items():
        if data.get('is_completed', False):
            continue
        items.append({
            'level_key': key,
            'level_name': data.get('level_name', key),
            'answered': data.get('answered_questions', 0),
            'total': data.get('total_questions', 0),
            'last_updated': data.get('last_updated', ''),
        })
    return JsonResponse({'progress': items})
    
    
    
    
@login_required
def practice_dashboard(request):
    """Get all practice progress for dashboard"""
    try:
        master = UserMasterProgress.objects.get(user=request.user)
        summary = master.get_all_progress_summary()
        
        total_sub_lessons = len(summary)
        total_answered = sum(s['answered_questions'] for s in summary)
        total_correct = sum(s['correct_count'] for s in summary)
        
        return JsonResponse({
            'success': True,
            'progress_list': summary,
            'statistics': {
                'total_sub_lessons': total_sub_lessons,
                'total_questions_answered': total_answered,
                'total_correct_answers': total_correct,
                'overall_accuracy': (total_correct / total_answered * 100) if total_answered > 0 else 0
            }
        })
        
    except UserMasterProgress.DoesNotExist:
        return JsonResponse({'success': True, 'progress_list': [], 'statistics': {}})

    
    
    
    
@login_required
def course_list_page(request):
    courses = Course.objects.all()
    course_name = UserCourseEnrollment.objects.filter(user=request.user).filter(status='active')
    course_ids = [i.course.id for i in course_name]
    print(course_ids)
    
    
    return render(
        request,
        "course/course_list.html",
        {
            "courses": courses,
            "course_ids":course_ids
        }
    )


@login_required
def course_detail_page(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    # Get related courses (excluding current course)
    related_courses = Course.objects.exclude(id=course_id)[:3]
    
    return render(
        request,
        "course/course_detail.html",
        {
            "course": course,
            "related_courses": related_courses
        }
    )




@login_required
@csrf_exempt
@require_http_methods(["POST"])
def submit_payment(request):
    """Handle payment submission"""
    try:
        # Get form data
        course_id = request.POST.get("course_id")
        payment_system = request.POST.get("payment_system")
        month = request.POST.get("month")
        transaction_id = request.POST.get("transaction_id", "").strip()
        
        # Validate all fields are present
        if not all([course_id, payment_system, month, transaction_id]):
            return JsonResponse({
                "status": False,
                "message": "All fields are required. Please fill in all information."
            })
        
        # Validate month is integer
        try:
            month = int(month)
            if month not in [1, 6, 12]:
                return JsonResponse({
                    "status": False,
                    "message": "Invalid duration selected. Please choose 1, 6, or 12 months."
                })
        except ValueError:
            return JsonResponse({
                "status": False,
                "message": "Invalid duration format."
            })
        
        # Check for duplicate transaction
        if Payment.objects.filter(
            transaction_id=transaction_id,
            payment_system=payment_system
        ).exists():
            return JsonResponse({
                "status": False,
                "message": "This transaction ID has already been submitted. Please check and try again."
            })
        
        # Get course
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": "Selected course not found."
            })
        
        # Calculate amount based on selected month
        if month == 1:
            amount = course.one_month_price
        elif month == 6:
            amount = course.six_month_price
        else:  # month == 12
            amount = course.one_year_price
        
        # Validate amount is not zero
        if amount <= 0:
            return JsonResponse({
                "status": False,
                "message": f"Invalid price for {month} month(s) duration. Please contact support."
            })
        
        # Create payment record
        payment = Payment.objects.create(
            user=request.user,
            course=course,
            payment_system=payment_system,
            month=month,
            transaction_id=transaction_id,
            amount=amount,
            status="pending"
        )
        
        return JsonResponse({
            "status": True,
            "message": "Payment submitted successfully! Your payment is pending verification. You will receive access within 24 hours after verification.",
            "payment_id": payment.id
        })
        
    except Exception as e:
        return JsonResponse({
            "status": False,
            "message": f"An error occurred: {str(e)}"
        }, status=400)


@login_required
def payment_history(request):
    """View payment history for the logged-in user"""
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'payments': payments,
        'total_payments': payments.count(),
        'total_spent': payments.filter(status='approved').aggregate(Sum('amount'))['amount__sum'] or 0,
    }
    return render(request, 'payments/payment_history.html', context)


@login_required
def payment_detail(request, payment_id):
    """View single payment details"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    context = {
        'payment': payment,
    }
    return render(request, 'payments/payment_detail.html', context)


@login_required
def payment_page(request,course_id):

    from .models import Course
    courses = Course.objects.all()
    
    context = {
        'courses': courses,
    }
    return render(request, 'payments/payment_detail.html', context)



@staff_member_required
def verify_payment(request, payment_id):
    """Admin view to verify payment"""
    if request.method == 'POST':
        payment = get_object_or_404(Payment, id=payment_id)
        action = request.POST.get('action')
        
        if action == 'approve':
            payment.status = 'approved'
            
            # Create or update enrollment for the user
            from django.utils import timezone

            from .models import UserCourseEnrollment

            # Calculate end date based on month duration
            end_date = timezone.now() + timezone.timedelta(days=payment.month * 30)
            
            enrollment, created = UserCourseEnrollment.objects.get_or_create(
                user=payment.user,
                course=payment.course,
                defaults={
                    'status': 'active',
                    'end_time': end_date
                }
            )
            
            if not created:
                # Extend existing enrollment
                enrollment.status = 'active'
                enrollment.end_time = max(enrollment.end_time, end_date)
                enrollment.save()
            
            payment.save()
            
            return JsonResponse({
                'status': True,
                'message': f'Payment approved. User {payment.user.username} now has access to {payment.course.name}.'
            })
            
        elif action == 'reject':
            payment.status = 'rejected'
            payment.save()
            
            return JsonResponse({
                'status': True,
                'message': f'Payment rejected for {payment.transaction_id}'
            })
    
    payment = get_object_or_404(Payment, id=payment_id)
    return render(request, 'admin/verify_payment.html', {'payment': payment})


@login_required
def user_profile(request):
    """Main profile page with inline editing"""
    
    user = request.user
    
    # Ensure user has a profile (create if not exists)
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    # Handle profile update (inline editing)
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        district = request.POST.get('district', '').strip()
        profile_image = request.FILES.get('profile_image')
        
        # Update user
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if email:
            user.email = email
        user.save()
        
        # Update profile
        profile.phone_number = phone_number if phone_number else ''
        profile.district = district if district else ''
        
        # Handle profile image
        if profile_image:
            if profile.profile_image:
                profile.profile_image.delete(save=False)
            profile.profile_image = profile_image
        
        profile.save()
        
        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Profile updated successfully!'
            })
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile_view')

    
    # GET request - display profile
    # Get user's enrollments
    enrollments = UserCourseEnrollment.objects.filter(
        user=user
    ).select_related('course').order_by('-enrolled_at')
    
    # Get active enrollments
    active_enrollments = enrollments.filter(status='active')
    
    # Get expired/completed enrollments
    past_enrollments = enrollments.filter(Q(status='expired') | Q(status='completed'))
    
    # Get payment history
    all_payments = Payment.objects.filter(user=user).order_by('-created_at')
    recent_payments = all_payments[:5]
    
    # Calculate total spent
    total_spent = all_payments.filter(status='approved').aggregate(
        Sum('amount')
    )['amount__sum'] or 0
    
    # Get exam statistics
    exam_attempts = ExamAttempt.objects.filter(user=user)
    total_exams = exam_attempts.count()
    
    # Calculate average score
    if total_exams > 0:
        avg_score_data = exam_attempts.aggregate(avg_score=Avg('score_percentage'))
        avg_score = avg_score_data['avg_score'] or 0
    else:
        avg_score = 0
    
    # Subject wise performance
    subject_performance = {}
    for subject in Subject.objects.all():
        subject_exams = exam_attempts.filter(subject=subject)
        if subject_exams.exists():
            avg_score_data = subject_exams.aggregate(avg_score=Avg('score_percentage'))
            subject_performance[subject.name] = {
                'attempts': subject_exams.count(),
                'avg_score': avg_score_data['avg_score'] or 0
            }
    
    subject_performance = dict(sorted(
        subject_performance.items(), 
        key=lambda x: x[1]['avg_score'], 
        reverse=True
    ))
    
    active_courses_count = active_enrollments.count()
    
    expiring_soon = active_enrollments.filter(
        end_time__lte=timezone.now() + timezone.timedelta(days=7),
        end_time__gt=timezone.now()
    )
    
    # Practice statistics
    try:
        master_progress = UserMasterProgress.objects.get(user=user)
        total_practice_answers = master_progress.total_questions_answered
        total_practice_correct = master_progress.total_correct_answers
        practice_accuracy = (total_practice_correct / total_practice_answers * 100) if total_practice_answers > 0 else 0
        completed_sub_lessons = sum(1 for data in master_progress.progress_data.values() if data.get('is_completed', False))
    except UserMasterProgress.DoesNotExist:
        total_practice_answers = 0
        total_practice_correct = 0
        practice_accuracy = 0
        completed_sub_lessons = 0
    
    context = {
        'profile_user': user,
        'profile': profile,
        'active_enrollments': active_enrollments[:3],
        'past_enrollments': past_enrollments[:3],
        'payments': recent_payments,
        'total_exams': total_exams,
        'avg_score': round(avg_score, 2),
        'subject_performance': subject_performance,
        'total_spent': total_spent,
        'active_courses_count': active_courses_count,
        'expiring_soon': expiring_soon,
        'total_practice_answers': total_practice_answers,
        'practice_accuracy': round(practice_accuracy, 1),
        'completed_sub_lessons': completed_sub_lessons,
    }
    
    return render(request, 'accounts/profile.html', context)

@login_required
def change_password(request):
    """Change user password"""
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Password changed successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def my_courses(request):
    """Show all courses user is enrolled in"""
    
    enrollments = UserCourseEnrollment.objects.filter(
        user=request.user
    ).select_related('course').order_by('-enrolled_at')
    
    # Filter by status
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        enrollments = enrollments.filter(status=status_filter)
    
    context = {
        'enrollments': enrollments,
        'status_filter': status_filter,
    }
    
    return render(request, 'accounts/my_courses.html', context)



@login_required
def my_exams(request):
    """Show all exam attempts by user with complete question details"""
    
    exam_attempts = ExamAttempt.objects.filter(
        user=request.user
    ).select_related('subject').order_by('-exam_date')
    
    # Serialize the data with complete question details
    exam_data = []
    for exam in exam_attempts:
        # Get all MCQ questions with their details
        questions = []
        for idx, mcq_id in enumerate(exam.mcq_ids_order):
            try:
                mcq = MCQ.objects.get(id=mcq_id)
                user_answer = exam.user_answers[idx] if idx < len(exam.user_answers) else None
                is_correct = exam.correct_status[idx] if idx < len(exam.correct_status) else False
                
                # Get all options
                options = [
                    {'number': 1, 'text': mcq.option_1},
                    {'number': 2, 'text': mcq.option_2},
                    {'number': 3, 'text': mcq.option_3},
                    {'number': 4, 'text': mcq.option_4},
                ]
                
                questions.append({
                    'id': mcq.id,
                    'question': mcq.question,
                    'options': options,
                    'user_answer': user_answer,
                    'correct_answer': mcq.correct_answer,
                    'is_correct': is_correct,
                    'explanation': mcq.explanation,
                })
            except MCQ.DoesNotExist:
                continue
        
        exam_data.append({
            'id': exam.id,
            'subject': {
                'id': exam.subject.id,
                'name': exam.subject.name
            } if exam.subject else None,
            'exam_date': exam.exam_date.isoformat(),
            'time_limit_minutes': exam.time_limit_minutes,
            'total_questions': exam.total_questions,
            'correct_answers': exam.correct_answers,
            'wrong_answers': exam.wrong_answers,
            'skipped_answers': exam.skipped_answers,
            'score_percentage': exam.score_percentage,
            'questions': questions,
        })
    
    # Pagination
    paginator = Paginator(exam_attempts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'exam_attempts': json.dumps(exam_data, cls=DjangoJSONEncoder),
        'page_obj': page_obj,
    }
    
    return render(request, 'accounts/my_exams.html', context)



def generate_question_pdf(request):
    if request.method == 'POST' and request.FILES.get('json_file'):
        json_file = request.FILES['json_file']
        data = json.load(json_file)

        # Handle both formats: bare list OR dict with 'questions' key
        if isinstance(data, list):
            questions = data
            total = len(data)
            exported_at = None
            selection = {}
        else:
            questions = data.get('questions', [])
            total = data.get('total', len(questions))
            exported_at = data.get('exported_at')
            selection = data.get('selection', {})

        for q in questions:
            q['has_previous_year'] = bool(q.get('previous_year'))

        context = {
            'institute_name':  request.POST.get('institute_name', 'Your Institute Name'),
            'exam_name':       request.POST.get('exam_name', 'MCQ Examination'),
            'total_questions': total,
            'total_marks':     total,
            'exported_at':     exported_at,
            'selection':       selection,
            'questions':       questions,
            'generated_at':    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        html_string = render_to_string('pdf/question_paper.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="question_paper.pdf"'
        pisa_status = pisa.CreatePDF(html_string, dest=response)
        if pisa_status.err:
            return HttpResponse('PDF generation error', status=500)
        return response

    return render(request, 'pdf/upload.html')


def generate_answer_pdf(request):
    if request.method == 'POST' and request.FILES.get('json_file'):
        json_file = request.FILES['json_file']
        data = json.load(json_file)

        # Handle both formats
        if isinstance(data, list):
            questions = data
            exported_at = None
        else:
            questions = data.get('questions', [])
            exported_at = data.get('exported_at')

        context = {
            'institute_name': request.POST.get('institute_name', 'Your Institute Name'),
            'exam_name':      request.POST.get('exam_name', 'MCQ Examination'),
            'questions':      questions,
            'generated_at':   datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'exported_at':    exported_at,
        }

        html_string = render_to_string('pdf/answer_sheet.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="answer_sheet.pdf"'
        pisa_status = pisa.CreatePDF(html_string, dest=response)
        if pisa_status.err:
            return HttpResponse('PDF generation error', status=500)
        return response

    return render(request, 'pdf/upload.html')