from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

# models.py


class Subject(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name


class Chapter(models.Model):
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="chapters",
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.subject.name if self.subject else 'No Subject'} -> {self.name}"


class Lesson(models.Model):
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="lessons",
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)
    
    def __str__(self):
        if self.chapter:
            return f"{self.chapter.name} -> {self.name}"
        return self.name


class SubLesson(models.Model):
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="sub_lessons",
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)
    mcq_count = models.IntegerField(default=0, db_index=True)
    
    def __str__(self):
        if self.lesson and self.lesson.chapter:
            return (
                f"Subject ({self.lesson.chapter.subject.name}) -> "
                f"Chapter ({self.lesson.chapter.name}) -> "
                f"Lesson ({self.lesson.name}) -> "
                f"Sub Lesson ({self.name})"
            )
        return self.name
    
    def update_mcq_count(self):
        """Update MCQ count based on related MCQs"""
        new_count = self.mcqs.count()
        if self.mcq_count != new_count:
            self.mcq_count = new_count
            self.save(update_fields=["mcq_count"])
        return self.mcq_count


class MCQ(models.Model):
    # Always required
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="mcqs"
    )
    
    # Optional levels (can be null)
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="mcqs",
        null=True,
        blank=True
    )
    
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="mcqs",
        null=True,
        blank=True
    )
    
    sub_lesson = models.ForeignKey(
        SubLesson,
        on_delete=models.CASCADE,
        related_name="mcqs",
        null=True,
        blank=True
    )
    
    question = models.TextField()
    
    option_1 = models.CharField(max_length=255)
    option_2 = models.CharField(max_length=255)
    option_3 = models.CharField(max_length=255)
    option_4 = models.CharField(max_length=255)
    
    previous_year = models.TextField(
        blank=True,
        null=True
    )
    
    correct_answer = models.IntegerField(
        help_text="Use 1, 2, 3, or 4"
    )
    
    explanation = models.TextField(
        blank=True,
        null=True
    )
    
    def __str__(self):
        return self.question[:50]
    
    def save(self, *args, **kwargs):
        """Optional validation logic: Ensure hierarchy is correct if levels exist"""
        if self.chapter and self.chapter.subject != self.subject:
            raise ValueError("Chapter does not belong to selected Subject")
        
        if self.lesson and self.chapter:
            if self.lesson.chapter != self.chapter:
                raise ValueError("Lesson does not belong to selected Chapter")
        
        if self.sub_lesson and self.lesson:
            if self.sub_lesson.lesson != self.lesson:
                raise ValueError("SubLesson does not belong to selected Lesson")
        
        super().save(*args, **kwargs)
    
    def get_options_list(self):
        """Returns list of options"""
        return [self.option_1, self.option_2, self.option_3, self.option_4]


@receiver(post_save, sender=MCQ)
def update_mcq_count_on_save(sender, instance, created, **kwargs):
    """Update sub_lesson.mcq_count when MCQ is created or updated"""
    if instance.sub_lesson:
        instance.sub_lesson.update_mcq_count()


@receiver(post_delete, sender=MCQ)
def update_mcq_count_on_delete(sender, instance, **kwargs):
    """Update sub_lesson.mcq_count when MCQ is deleted"""
    if instance.sub_lesson:
        instance.sub_lesson.update_mcq_count()

class Course(models.Model):

    name = models.CharField(max_length=255)
    description = models.TextField()

    # multiple subjects inside one course
    subjects = models.ManyToManyField(
        Subject,
        related_name="courses"
    )

    image = models.ImageField(
        upload_to="courses/",
        blank=True,
        null=True
    )

    total_subjects = models.PositiveIntegerField(
        default=0
    )

    total_questions = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )
    one_month_price = models.IntegerField(default=0)
    six_month_price = models.IntegerField(default=0)
    one_year_price = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        """
        Optional auto update logic
        """
        super().save(*args, **kwargs)

        self.total_subjects = self.subjects.count()

        self.total_questions = MCQ.objects.filter(
            sub_lesson__lesson__chapter__subject__in=self.subjects.all()
        ).count()

        super().save(update_fields=[
            "total_subjects",
            "total_questions"
        ])

    def __str__(self):
        return self.name

class UserCourseEnrollment(models.Model):


    STATUS_CHOICES = (
        ("active", "Active"),
        ("completed", "Completed"),
        ("expired", "Expired"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="course_enrollments"
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )

    start_time = models.DateTimeField()

    end_time = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active"
    )

    enrolled_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.username} -> {self.course.name}"
    def save(self, *args, **kwargs):
        if self.end_time and self.end_time < timezone.now():
            self.status = "expired"
        else:
            self.status = "active"

        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.end_time

    def __str__(self):
        return f"{self.user.username} -> {self.course.name}"

# exam mode
class ExamAttempt(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='exam_attempts'
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        related_name='exam_attempts'
    )

    exam_date = models.DateTimeField(
        auto_now_add=True
    )

    # Exam configuration
    time_limit_minutes = models.IntegerField(default=10)
    total_questions = models.IntegerField()

    # Results
    correct_answers = models.IntegerField(default=0)
    wrong_answers = models.IntegerField(default=0)
    skipped_answers = models.IntegerField(default=0)
    score_percentage = models.FloatField(default=0)

    # JSON storage
    mcq_ids_order = models.JSONField(default=list)
    user_answers = models.JSONField(default=list)
    correct_status = models.JSONField(default=list)

    selected_chapters = models.JSONField(default=list)
    selected_sub_lessons = models.JSONField(default=list)

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"Exam {self.id} - "
            f"{self.exam_date} - "
            f"{self.score_percentage}%"
        )

    class Meta:
        ordering = ['-exam_date']
        




class UserMasterProgress(models.Model):
 
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        primary_key=True,
        related_name='master_progress'
    )
    
    
    progress_data = models.JSONField(default=dict)
    
    # Quick statistics (denormalized for faster display)
    total_sub_lessons = models.IntegerField(default=0)
    total_questions_answered = models.IntegerField(default=0)
    total_correct_answers = models.IntegerField(default=0)
    
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['-last_updated']),
            models.Index(fields=['user', '-last_updated']),
        ]
    
    def get_sublesson_progress(self, sub_lesson_id):
        """
        Get progress for a specific sub-lesson
        Returns: dict or empty dict if not found
        """
        return self.progress_data.get(str(sub_lesson_id), {})
    
    def save_progress(self, sub_lesson_id, total_questions, answered, 
                      current_q_index, user_answers, questions_order, 
                      correct_count=0, wrong_count=0, random_order=False):
        """
        Save progress for a sub-lesson (PRACTICE MODE ONLY)
        Called when user clicks "Remember Me" button
        """
        sub_id_str = str(sub_lesson_id)
        
        # Calculate accuracy
        accuracy = (correct_count / answered * 100) if answered > 0 else 0
        
        # Build progress data
        self.progress_data[sub_id_str] = {
            # Core progress
            'total_questions': total_questions,
            'answered_questions': answered,
            'current_index': current_q_index,
            'user_answers': user_answers,
            'questions_order': questions_order,
            
            # Performance stats
            'correct_count': correct_count,
            'wrong_count': wrong_count,
            'accuracy': accuracy,
            
            # Settings
            'random_order': random_order,
            
            # Tracking
            'last_question_id': questions_order[current_q_index] if questions_order and current_q_index < len(questions_order) else None,
            'last_question_index': current_q_index,
            
            # Timestamps
            'started_at': self.progress_data.get(sub_id_str, {}).get('started_at', datetime.now().isoformat()),
            'updated_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat() if answered >= total_questions else None,
            
            # Status
            'is_completed': answered >= total_questions,
            'is_paused': answered > 0 and answered < total_questions,
        }
        
        # Update global statistics
        self._update_statistics()
        self.save()
        
        return True
    
    def update_answer(self, sub_lesson_id, question_index, answer, is_correct, question_id):
        """
        Update a single answer in memory (does NOT save to DB automatically)
        Returns: bool (True if updated, False if already answered)
        """
        sub_id_str = str(sub_lesson_id)
        
        if sub_id_str not in self.progress_data:
            return False
        
        data = self.progress_data[sub_id_str]
        
        # Initialize user_answers if not exists
        if 'user_answers' not in data:
            data['user_answers'] = []
        
        # Extend list if needed
        while len(data['user_answers']) <= question_index:
            data['user_answers'].append(None)
        
        # Only update if not already answered
        if data['user_answers'][question_index] is not None:
            return False
        
        # Save the answer
        data['user_answers'][question_index] = answer
        data['answered_questions'] = data.get('answered_questions', 0) + 1
        
        # Update counts
        if is_correct:
            data['correct_count'] = data.get('correct_count', 0) + 1
        else:
            data['wrong_count'] = data.get('wrong_count', 0) + 1
        
        # Update accuracy
        answered = data['answered_questions']
        data['accuracy'] = (data['correct_count'] / answered * 100) if answered > 0 else 0
        
        # Update current index if this was the current question
        if question_index == data.get('current_index', 0):
            data['current_index'] = question_index + 1
            data['last_question_id'] = question_id
            data['last_question_index'] = question_index
        
        # Check if completed
        if data['answered_questions'] >= data.get('total_questions', 0):
            data['is_completed'] = True
            data['completed_at'] = datetime.now().isoformat()
        
        data['updated_at'] = datetime.now().isoformat()
        
        # Note: We don't save here - user must click "Remember Me" to save
        return True
    
    def load_progress(self, sub_lesson_id):
        """
        Load saved progress for a specific sub-lesson
        Returns: dict or None if no progress or already completed
        """
        sub_id_str = str(sub_lesson_id)
        data = self.progress_data.get(sub_id_str, {})
        
        if not data:
            return None
        
        if data.get('is_completed', False):
            return None
        
        return {
            'exists': True,
            'total_questions': data.get('total_questions', 0),
            'answered_questions': data.get('answered_questions', 0),
            'remaining_questions': data.get('total_questions', 0) - data.get('answered_questions', 0),
            'current_index': data.get('current_index', 0),
            'user_answers': data.get('user_answers', []),
            'questions_order': data.get('questions_order', []),
            'correct_count': data.get('correct_count', 0),
            'wrong_count': data.get('wrong_count', 0),
            'accuracy': data.get('accuracy', 0),
            'random_order': data.get('random_order', False),
            'progress_percentage': (data.get('answered_questions', 0) / data.get('total_questions', 1)) * 100,
            'is_paused': data.get('is_paused', False),
            'last_updated': data.get('updated_at', ''),
            'started_at': data.get('started_at', ''),
        }
    
    def delete_progress(self, sub_lesson_id):
        """
        Delete progress for a specific sub-lesson (Start Fresh)
        Returns: bool (True if deleted, False if not found)
        """
        sub_id_str = str(sub_lesson_id)
        
        if sub_id_str in self.progress_data:
            del self.progress_data[sub_id_str]
            self._update_statistics()
            self.save()
            return True
        return False
    
    def get_all_progress_summary(self):

        from .models import SubLesson
        
        if not self.progress_data:
            return []
        
  
        sub_ids = [int(k) for k in self.progress_data.keys()]
        sub_lessons = SubLesson.objects.filter(id__in=sub_ids).select_related(
            'lesson__chapter__subject'
        )
        
        sub_map = {sl.id: sl for sl in sub_lessons}
        summary = []
        for sub_id_str, data in self.progress_data.items():
            sub_id = int(sub_id_str)
            sub = sub_map.get(sub_id)
            
            if sub:
                answered = data.get('answered_questions', 0)
                total = data.get('total_questions', 0)
                
                summary.append({
                    'sub_lesson_id': sub_id,
                    'sub_lesson_name': sub.name,
                    'lesson_name': sub.lesson.name,
                    'chapter_name': sub.lesson.chapter.name,
                    'subject_name': sub.lesson.chapter.subject.name,
                    'total_questions': total,
                    'answered_questions': answered,
                    'correct_count': data.get('correct_count', 0),
                    'wrong_count': data.get('wrong_count', 0),
                    'percentage': (answered / total * 100) if total > 0 else 0,
                    'accuracy': data.get('accuracy', 0),
                    'random_order': data.get('random_order', False),
                    'is_completed': data.get('is_completed', False),
                    'last_updated': data.get('updated_at', ''),
                })
        
        return summary
    
    def _update_statistics(self):
  
        total_subs = len(self.progress_data)
        total_answered = 0
        total_correct = 0
        
        for sub_id, data in self.progress_data.items():
            total_answered += data.get('answered_questions', 0)
            total_correct += data.get('correct_count', 0)
        
        self.total_sub_lessons = total_subs
        self.total_questions_answered = total_answered
        self.total_correct_answers = total_correct
    
    def reset_all_progress(self):
    
        self.progress_data = {}
        self.total_sub_lessons = 0
        self.total_questions_answered = 0
        self.total_correct_answers = 0
        self.save()
    
    def __str__(self):
        return f"{self.user.username}: {self.total_sub_lessons} sub-lessons, {self.total_questions_answered} answers"


@receiver(post_save, sender=User)
def create_user_master_progress(sender, instance, created, **kwargs):
    if created:
        UserMasterProgress.objects.get_or_create(user=instance)

from datetime import timedelta
from django.db import models
from django.utils import timezone


class TransactionVerification(models.Model):
    PAYMENT_SYSTEM_CHOICES = (
        ("bkash", "Bkash"),
        ("nagad", "Nagad"),
        ("rocket", "Rocket"),
    )

    is_complete = models.BooleanField(default=False)

    payment_system = models.CharField(
        max_length=20,
        choices=PAYMENT_SYSTEM_CHOICES
    )

    transaction_id = models.CharField(
        max_length=200,
        unique=True
    )

    amount = models.IntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):
        # first save TransactionVerification
        super().save(*args, **kwargs)

        # find matching pending payments
        matching_payments = Payment.objects.filter(
            payment_system=self.payment_system,
            transaction_id=self.transaction_id,
            amount=self.amount,
            status="pending"
        )

        for payment in matching_payments:
            # approve payment
            payment.status = "approved"
            payment.verified_transaction = self
            payment.save()

            # enrollment duration by month
            start_time = timezone.now()

            if payment.month == 1:
                end_time = start_time + timedelta(days=30)

            elif payment.month == 6:
                end_time = start_time + timedelta(days=180)

            else:
                end_time = start_time + timedelta(days=365)

            # create or update enrollment
            enrollment, created = UserCourseEnrollment.objects.get_or_create(
                user=payment.user,
                course=payment.course,
                defaults={
                    "start_time": start_time,
                    "end_time": end_time,
                    "status": "active"
                }
            )

            # if already exists → extend time
            if not created:
                if enrollment.end_time > timezone.now():
                    enrollment.end_time = enrollment.end_time + (
                        end_time - start_time
                    )
                else:
                    enrollment.start_time = start_time
                    enrollment.end_time = end_time

                enrollment.status = "active"
                enrollment.save()

        # mark verification complete
        if matching_payments.exists():
            self.is_complete = True
            super().save(update_fields=["is_complete"])

    def __str__(self):
        return f"{self.payment_system} - {self.transaction_id}"

   
    
    
    def get_duration_display(self):
        """Return human readable duration"""
        if self.month == 1:
            return "1 Month"
        elif self.month == 6:
            return "6 Months"
        else:
            return "12 Months"
    
    def get_status_badge_class(self):
        """Return CSS class for status badge"""
        if self.status == 'approved':
            return 'bg-green-100 text-green-700 border-green-200'
        elif self.status == 'pending':
            return 'bg-yellow-100 text-yellow-700 border-yellow-200'
        else:
            return 'bg-red-100 text-red-700 border-red-200'
    
    
    
class Payment(models.Model):
    PAYMENT_SYSTEM_CHOICES = (
        ("bkash", "Bkash"),
        ("nagad", "Nagad"),
        ("rocket", "Rocket"),
    )

    MONTH_CHOICES = (
        (1, "1 Month"),
        (6, "6 Months"),
        (12, "12 Months"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE
    )

    payment_system = models.CharField(
        max_length=20,
        choices=PAYMENT_SYSTEM_CHOICES
    )

    month = models.IntegerField(
        choices=MONTH_CHOICES
    )

    transaction_id = models.CharField(
        max_length=200
    )

    amount = models.IntegerField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    verified_transaction = models.ForeignKey(
        TransactionVerification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
        models.UniqueConstraint(
            fields=["transaction_id", "payment_system"],
            name="unique_transaction_payment_system"
        )
    ]
    def __str__(self):
        return f"{self.user.username} - {self.course.name}"
    
    
    



class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Profile fields
    profile_image = models.ImageField(
        upload_to='profile_pictures/', 
        blank=True, 
        null=True,
        default='defaults/default-avatar.png'
    )
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional info
    bio = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
    
    @property
    def profile_image_url(self):
        if self.profile_image and hasattr(self.profile_image, 'url'):
            return self.profile_image.url
        return '/static/images/default-avatar.png'

# Auto-create profile when user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()