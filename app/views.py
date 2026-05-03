from django.shortcuts import render, redirect
import json
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.shortcuts import render
from .models import UserMasterProgress, SubLesson, MCQ, Lesson, Chapter, Subject
import json
import random
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Subject, Chapter, Lesson, SubLesson, MCQ, ExamAttempt
import random
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Payment, TransactionVerification
from .models import Course, Payment
from app.models import UserCourseEnrollment
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from .models import (
    UserCourseEnrollment, 
    Payment, 
    ExamAttempt,
    Course,
    Subject
)
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Avg
from django.utils import timezone
from django.contrib import messages
from .models import (
    User, UserProfile, UserCourseEnrollment, Payment, 
    ExamAttempt, Subject, UserMasterProgress
)
def Home_page(request):
    return render(request,'index.html')
def Contact_page(request):
    return render(request,'contact.html')
def Features_page(request):
    return render(request,'features.html')
def Faq_page(request):
    return render(request,'faq.html')




# questine upload
def upload_mcq(request):
    if request.method == "POST":
        sub_lesson_id = request.POST.get("sub_lesson")
        json_data = request.POST.get("json_data")

        try:
            sub_lesson = SubLesson.objects.get(id=sub_lesson_id)
            data = json.loads(json_data)

            if not isinstance(data, list):
                raise ValueError("JSON must be a list")

            # 🔥 Option mapping
            option_map = {
                "ক": 1,
                "খ": 2,
                "গ": 3,
                "ঘ": 4
            }

            mcq_list = []

            for item in data:
                options = item.get("options", {})

                mcq_list.append(
                    MCQ(
                        sub_lesson=sub_lesson,
                        question=item['question'],

                        option_1=options.get("ক", ""),
                        option_2=options.get("খ", ""),
                        option_3=options.get("গ", ""),
                        option_4=options.get("ঘ", ""),

                        correct_answer=option_map.get(item.get("answer"), 1),

                        explanation=item.get("explanation", ""),
                        previous_year=item.get("previous_exam", "")
                    )
                )

            with transaction.atomic():
                MCQ.objects.bulk_create(mcq_list)

            return render(request, 'upload.html', {
                'subjects': Subject.objects.all(),
                'success': "MCQs uploaded successfully!"
            })

        except Exception as e:
            return render(request, 'upload.html', {
                'subjects': Subject.objects.all(),
                'error': str(e)
            })

    return render(request, 'upload.html', {
        'subjects': Subject.objects.all()
    })
  
  



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



@login_required

def exam_home(request):
    # only active + not expired enrollments
    enrollments = UserCourseEnrollment.objects.filter(
        user=request.user,
        status="active",
       
    ).select_related(
        'course'
    ).prefetch_related(
        'course__subjects'
    )

    # IMPORTANT:
    # previous query was fetching all subjects of user
    # without checking active enrollment properly

    subjects = Subject.objects.filter(
        courses__enrollments__in=enrollments
    ).distinct()

    total_subject = subjects.count()
    if total_subject==0:
        messages.error(
        request,
        "First Enroll Please"
    )
       
    
        return redirect("course_list_page")
    return render(
        request,
        'exam/home.html',
        {
            'subjects': subjects,
            'user': request.user,
            "total_subject":total_subject
        }
    )

@login_required
def get_chapters_api(request):
    """Get chapters for a subject"""
    subject_id = request.GET.get('subject_id')
    if not subject_id:
        return JsonResponse([], safe=False)
    chapters = Chapter.objects.filter(subject_id=subject_id).values('id', 'name')
    return JsonResponse(list(chapters), safe=False)


@login_required
@csrf_exempt
def get_lessons_api(request):
    """Get lessons for selected chapters"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            chapter_ids = data.get('chapter_ids', [])
        except:
            chapter_ids = []
    else:
        chapter_ids = request.GET.getlist('chapter_ids[]')
        if not chapter_ids:
            chapter_ids = request.GET.getlist('chapter_ids')
    
    if not chapter_ids:
        return JsonResponse([], safe=False)
    
    try:
        chapter_ids = [int(cid) for cid in chapter_ids if cid]
    except ValueError:
        return JsonResponse([], safe=False)
    
    # Get Lessons (not SubLessons) - these are the middle level
    lessons = Lesson.objects.filter(chapter_id__in=chapter_ids).values('id', 'name', 'chapter_id')
    return JsonResponse(list(lessons), safe=False)

@login_required
@csrf_exempt
def get_sub_lessons_api(request):
    """Get SubLessons for selected lessons with MCQ counts"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lesson_ids = data.get('lesson_ids', [])
        except:
            lesson_ids = []
    else:
        lesson_ids = request.GET.getlist('lesson_ids[]')
        if not lesson_ids:
            lesson_ids = request.GET.getlist('lesson_ids')
    
    if not lesson_ids:
        return JsonResponse([], safe=False)
    
    try:
        lesson_ids = [int(lid) for lid in lesson_ids if lid]
    except ValueError:
        return JsonResponse([], safe=False)
    
    # Get SubLessons for selected lessons with mcq_count
    sub_lessons = SubLesson.objects.filter(lesson_id__in=lesson_ids).values(
        'id', 
        'name', 
        'lesson_id',
        'mcq_count'  # ← Add this line
    )
    return JsonResponse(list(sub_lessons), safe=False)

@login_required
@csrf_exempt
def get_mcqs_api(request):
    """Get random MCQs from selected sub-lessons"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            sub_lesson_ids = data.get('sub_lesson_ids', [])
            question_count = data.get('question_count', 10)
        except:
            sub_lesson_ids = []
            question_count = 10
    else:
        sub_lesson_ids = request.GET.getlist('sub_lesson_ids[]')
        if not sub_lesson_ids:
            sub_lesson_ids = request.GET.getlist('sub_lesson_ids')
        question_count = request.GET.get('question_count', 10)
    
    try:
        question_count = int(question_count)
        if question_count > 100:
            question_count = 100
        if question_count < 1:
            question_count = 1
    except ValueError:
        question_count = 10
    
    if not sub_lesson_ids:
        return JsonResponse({'questions': [], 'total': 0, 'mcq_ids': []})
    
    try:
        sub_lesson_ids = [int(sid) for sid in sub_lesson_ids if sid]
    except ValueError:
        return JsonResponse({'questions': [], 'total': 0, 'mcq_ids': []})
    
    mcqs = MCQ.objects.filter(sub_lesson_id__in=sub_lesson_ids)
    mcq_list = list(mcqs)
    
    if len(mcq_list) > question_count:
        mcq_list = random.sample(mcq_list, question_count)
    
    mcq_ids_order = [mcq.id for mcq in mcq_list]
    
    questions_data = []
    for mcq in mcq_list:
        questions_data.append({
            'id': mcq.id,
            'question': mcq.question,
            'options': [mcq.option_1, mcq.option_2, mcq.option_3, mcq.option_4],
            'correct_answer': mcq.correct_answer,
            'explanation': mcq.explanation or '',
        })
    
    return JsonResponse({
        'questions': questions_data,
        'total': len(questions_data),
        'mcq_ids': mcq_ids_order
    })


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def save_exam_result_api(request):

    try:
        data = json.loads(request.body)
        
        subject_id = data.get('subject_id')
        subject = None
        if subject_id:
            try:
                subject = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                pass
        
        exam_attempt = ExamAttempt.objects.create(
            user=request.user,
            subject=subject,
            time_limit_minutes=data.get('time_limit_minutes', 10),
            total_questions=data.get('total_questions', 0),
            correct_answers=data.get('correct_answers', 0),
            wrong_answers=data.get('wrong_answers', 0),
            skipped_answers=data.get('skipped_answers', 0),
            score_percentage=data.get('score_percentage', 0),
            mcq_ids_order=data.get('mcq_ids_order', []),
            user_answers=data.get('user_answers', []),
            correct_status=data.get('correct_status', []),
            selected_chapters=data.get('selected_chapters', []),
            selected_sub_lessons=data.get('selected_sub_lessons', [])
        )
        
        return JsonResponse({
            'success': True,
            'exam_id': exam_attempt.id,
            'message': 'পরীক্ষার ফলাফল সফলভাবে সংরক্ষণ করা হয়েছে'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

# these practice mode views

@login_required
@csrf_exempt
def practice_page(request):
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
    return render(request, 'exam/practice.html', {'subjects': subjects})

@login_required
@csrf_exempt
def get_mcqs_api_practice(request):
    """Get random MCQs from selected sub-lessons"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            sub_lesson_ids = data.get('sub_lesson_ids', [])
            question_count = data.get('question_count', 10)
        except:
            sub_lesson_ids = []
            question_count = 10
    else:
        sub_lesson_ids = request.GET.getlist('sub_lesson_ids[]')
        if not sub_lesson_ids:
            sub_lesson_ids = request.GET.getlist('sub_lesson_ids')
        question_count = request.GET.get('question_count', 10)
    
    try:
        question_count = int(question_count)
        if question_count < 1:
            question_count = 1
    except ValueError:
        question_count = 10
    
    if not sub_lesson_ids:
        return JsonResponse({'questions': [], 'total': 0, 'mcq_ids': []})
    
    try:
        sub_lesson_ids = [int(sid) for sid in sub_lesson_ids if sid]
    except ValueError:
        return JsonResponse({'questions': [], 'total': 0, 'mcq_ids': []})
    
    mcqs = MCQ.objects.filter(sub_lesson_id__in=sub_lesson_ids)
    mcq_list = list(mcqs)
    
    if len(mcq_list) > question_count:
        mcq_list = random.sample(mcq_list, question_count)
    
    mcq_ids_order = [mcq.id for mcq in mcq_list]
    
    questions_data = []
    for mcq in mcq_list:
        questions_data.append({
            'id': mcq.id,
            'question': mcq.question,
            'options': [mcq.option_1, mcq.option_2, mcq.option_3, mcq.option_4],
            'correct_answer': mcq.correct_answer,
            'explanation': mcq.explanation or '',
        })
    
    return JsonResponse({
        'questions': questions_data,
        'total': len(questions_data),
        'mcq_ids': mcq_ids_order
    })



def get_practice_progress(request):
    if request.method == 'GET':
        sub_lesson_id = request.GET.get('sub_lesson_id')
        
        if not sub_lesson_id:
            return JsonResponse({'error': 'sub_lesson_id required'}, status=400)
        
        try:
            master = UserMasterProgress.objects.get(user=request.user)
            progress = master.load_progress(sub_lesson_id)
            
            if progress:
                return JsonResponse(progress)
            else:
                return JsonResponse({'exists': False})
                
        except UserMasterProgress.DoesNotExist:
            return JsonResponse({'exists': False})


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def save_practice_progress(request):
    """Save practice progress (called when user clicks Remember Me)"""
    try:
        data = json.loads(request.body)
        
        sub_lesson_id = data.get('sub_lesson_id')
        total_questions = data.get('total_questions', 0)
        answered_questions = data.get('answered_questions', 0)
        current_index = data.get('current_index', 0)
        user_answers = data.get('user_answers', [])
        questions_order = data.get('questions_order', [])
        correct_count = data.get('correct_count', 0)
        wrong_count = data.get('wrong_count', 0)
        random_order = data.get('random_order', False)
        
        # Get or create master progress
        master, created = UserMasterProgress.objects.get_or_create(user=request.user)
        
        # Save progress
        master.save_progress(
            sub_lesson_id=sub_lesson_id,
            total_questions=total_questions,
            answered=answered_questions,
            current_q_index=current_index,
            user_answers=user_answers,
            questions_order=questions_order,
            correct_count=correct_count,
            wrong_count=wrong_count,
            random_order=random_order
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Progress saved successfully',
            'answered': answered_questions,
            'total': total_questions,
            'percentage': (answered_questions / total_questions * 100) if total_questions > 0 else 0
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def delete_practice_progress(request):
    """Delete practice progress (Start Fresh)"""
    try:
        data = json.loads(request.body)
        sub_lesson_id = data.get('sub_lesson_id')
        
        master = UserMasterProgress.objects.get(user=request.user)
        deleted = master.delete_progress(sub_lesson_id)
        
        return JsonResponse({
            'success': True,
            'deleted': deleted,
            'message': 'Progress deleted. Starting fresh!'
        })
        
    except UserMasterProgress.DoesNotExist:
        return JsonResponse({'success': True, 'message': 'No progress to delete'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@csrf_exempt
def get_mcqs_by_ids(request):
    """Get specific MCQs by IDs (for resuming practice)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            mcq_ids = data.get('mcq_ids', [])
        except:
            mcq_ids = []
    
    if not mcq_ids:
        return JsonResponse({'questions': []}, safe=False)
    
    # Get MCQs in the exact order
    mcq_dict = {mcq.id: mcq for mcq in MCQ.objects.filter(id__in=mcq_ids)}
    ordered_mcqs = [mcq_dict[mid] for mid in mcq_ids if mid in mcq_dict]
    
    questions_data = []
    for mcq in ordered_mcqs:
        questions_data.append({
            'id': mcq.id,
            'question': mcq.question,
            'options': [mcq.option_1, mcq.option_2, mcq.option_3, mcq.option_4],
            'correct_answer': mcq.correct_answer,
            'explanation': mcq.explanation or '',
        })
    
    return JsonResponse({'questions': questions_data})


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


# -----------------------------------
# Payment page for single course
# -----------------------------------
# views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Payment, Course, TransactionVerification
import json

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


# Admin views for payment verification
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def verify_payment(request, payment_id):
    """Admin view to verify payment"""
    if request.method == 'POST':
        payment = get_object_or_404(Payment, id=payment_id)
        action = request.POST.get('action')
        
        if action == 'approve':
            payment.status = 'approved'
            
            # Create or update enrollment for the user
            from .models import UserCourseEnrollment
            from django.utils import timezone
            
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

# views.py


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

import json
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import ExamAttempt, MCQ

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