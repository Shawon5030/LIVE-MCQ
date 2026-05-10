# admin.py
from django.contrib import admin
from django.db.models import Count
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html

from .models import (MCQ, Chapter, Course, ExamAttempt, Lesson, Payment,
                     Subject, SubLesson, TransactionVerification,
                     UserCourseEnrollment, UserMasterProgress)

mod = [ Subject, Chapter, Lesson, SubLesson, MCQ, ExamAttempt, 
    Course, UserCourseEnrollment, Payment, TransactionVerification,UserMasterProgress]

for i in mod:
    admin.site.register(i)