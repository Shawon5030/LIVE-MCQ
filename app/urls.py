from django.urls import path
from app.views import *
from app import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
urlpatterns = [
    
    
    path('',Home_page,name='home_page'),
    path('contact/',Contact_page,name='contact'),
    path('features/',Features_page,name='features'),
    path('faq/',Faq_page,name='faq'),
    path('upload-mcq/', upload_mcq, name='upload_mcq'),


    
  
    
    path('accounts/login/', views.login_page, name='login_page'),
    path('register/', views.register_page, name='register_page'),
    path('api/login/', views.login_api, name='login_api'),
    path('api/register/', views.register_api, name='register_api'),
    path('api/logout/', views.logout_api, name='logout_api'),
    
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='password/password_reset.html'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password/password_reset_complete.html'
    ), name='password_reset_complete'),
    
     path(
        "courses/",
        views.course_list_page,
        name="course_list_page"
    ),

    path(
        "course/<int:course_id>/",
        views.course_detail_page,
        name="course_detail"
    ),

    path(
        "payment/<int:course_id>/",
        views.payment_page,
        name="payment_page"
    ),

    path(
        "submit-payment/",
        views.submit_payment,
        name="submit_payment"
    ),
    
    # Exam URLs (all require login)
    path('exam/', views.exam_home, name='exam_home'),
    path('api/chapters/', views.get_chapters_api, name='api_chapters'),
    path('api/lessons/', views.get_lessons_api, name='api_lessons'),
    path('api/sub-lessons/', views.get_sub_lessons_api, name='api_sub_lessons'),  # New endpoint
    path('api/mcqs/', views.get_mcqs_api, name='api_mcqs'),
    path('api/save-exam-result/', views.save_exam_result_api, name='save_exam_result'),
    
  
   
   
   

    path('payment/submit/', views.submit_payment, name='submit_payment'),
    path('payment/history/', views.payment_history, name='payment_history'),
    path('payment/<int:payment_id>/', views.payment_detail, name='payment_detail'),
    
    # Admin payment verification
    path('admin/payment/verify/<int:payment_id>/', views.verify_payment, name='verify_payment'),
    
    path('profile/', views.user_profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('my-courses/', views.my_courses, name='my_courses'),
    path('my-exams/', views.my_exams, name='my_exams'),
    

    # Practice URLs
    path('practice/', views.practice_page, name='practice_page'),
    path('api/mcq/practice/', views.get_mcqs_api_practice, name='get_mcqs_api_practice'),
    path('api/practice/progress/', views.get_practice_progress, name='get_practice_progress'),
    path('api/practice/save/', views.save_practice_progress, name='save_practice_progress'),
    path('api/practice/delete/', views.delete_practice_progress, name='delete_practice_progress'),
    path('api/practice/mcqs-by-ids/', views.get_mcqs_by_ids, name='get_mcqs_by_ids'),
    path('api/practice/dashboard/', views.practice_dashboard, name='practice_dashboard'),
    
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )