"""
Virtual Classroom System - Domain-Driven Design Implementation
Similar to Google Classroom
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4


# ============================================================================
# VALUE OBJECTS
# ============================================================================

@dataclass(frozen=True)
class AccessCode:
    """Value Object representing a course access code"""
    value: str
    
    def __post_init__(self):
        if not self.value or len(self.value) < 6:
            raise ValueError("Access code must be at least 6 characters")


@dataclass(frozen=True)
class Grade:
    """Value Object representing a grade"""
    points: float
    max_points: float
    
    def __post_init__(self):
        if self.points < 0 or self.max_points <= 0:
            raise ValueError("Invalid grade values")
        if self.points > self.max_points:
            raise ValueError("Points cannot exceed max points")
    
    def percentage(self) -> float:
        return (self.points / self.max_points) * 100


# ============================================================================
# ENUMS
# ============================================================================

class CourseStatus(Enum):
    """Status of a course"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"


class UserRole(Enum):
    """Role of a user in a course"""
    TEACHER = "teacher"
    STUDENT = "student"


class SubmissionStatus(Enum):
    """Status of an assignment submission"""
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    GRADED = "graded"
    LATE = "late"


class ContentVisibility(Enum):
    """Visibility of course content"""
    ALL = "all"  # Visible to all course members
    TEACHERS_ONLY = "teachers_only"


# ============================================================================
# ENTITIES
# ============================================================================

@dataclass
class User:
    """Entity representing a user (teacher or student)"""
    id: UUID
    name: str
    email: str
    
    def __eq__(self, other):
        if not isinstance(other, User):
            return False
        return self.id == other.id


@dataclass
class CourseEnrollment:
    """Entity representing a student's enrollment in a course"""
    id: UUID
    user: User
    role: UserRole
    enrolled_at: datetime = field(default_factory=datetime.now)
    
    def is_teacher(self) -> bool:
        return self.role == UserRole.TEACHER
    
    def is_student(self) -> bool:
        return self.role == UserRole.STUDENT
    
    def __eq__(self, other):
        if not isinstance(other, CourseEnrollment):
            return False
        return self.id == other.id


@dataclass
class Announcement:
    """Entity representing a course announcement"""
    id: UUID
    title: str
    content: str
    created_by: User
    created_at: datetime = field(default_factory=datetime.now)
    visibility: ContentVisibility = ContentVisibility.ALL
    
    def is_visible_to(self, role: UserRole) -> bool:
        """Check if announcement is visible to given role"""
        if self.visibility == ContentVisibility.ALL:
            return True
        return role == UserRole.TEACHER
    
    def __eq__(self, other):
        if not isinstance(other, Announcement):
            return False
        return self.id == other.id


@dataclass
class Material:
    """Entity representing learning material"""
    id: UUID
    title: str
    description: str
    content_url: Optional[str]
    created_by: User
    created_at: datetime = field(default_factory=datetime.now)
    visibility: ContentVisibility = ContentVisibility.ALL
    
    def is_visible_to(self, role: UserRole) -> bool:
        """Check if material is visible to given role"""
        if self.visibility == ContentVisibility.ALL:
            return True
        return role == UserRole.TEACHER
    
    def __eq__(self, other):
        if not isinstance(other, Material):
            return False
        return self.id == other.id


# ============================================================================
# AGGREGATES
# ============================================================================

@dataclass
class Course:
    """
    Aggregate Root representing a course.
    Manages enrollments, content, and course lifecycle.
    """
    id: UUID
    name: str
    description: str
    created_by: User
    access_code: AccessCode
    status: CourseStatus = CourseStatus.DRAFT
    max_students: Optional[int] = None
    enrollments: List[CourseEnrollment] = field(default_factory=list)
    announcements: List[Announcement] = field(default_factory=list)
    materials: List[Material] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Ensure creator is enrolled as teacher"""
        if not any(e.user == self.created_by and e.is_teacher() 
                  for e in self.enrollments):
            teacher_enrollment = CourseEnrollment(
                id=uuid4(),
                user=self.created_by,
                role=UserRole.TEACHER
            )
            self.enrollments.append(teacher_enrollment)
    
    def is_active(self) -> bool:
        """Check if course is active"""
        return self.status == CourseStatus.ACTIVE
    
    def can_accept_students(self) -> bool:
        """Check if course can accept more students"""
        if not self.is_active():
            return False
        
        if self.max_students is None:
            return True
        
        student_count = sum(1 for e in self.enrollments if e.is_student())
        return student_count < self.max_students
    
    def enroll_student(self, user: User, provided_code: str) -> CourseEnrollment:
        """
        Enroll a student in the course.
        Validates access code, course status, and enrollment limits.
        """
        # Validation: Course must be active
        if not self.is_active():
            raise ValueError(f"Course '{self.name}' is not active")
        
        # Validation: Access code must match
        if provided_code != self.access_code.value:
            raise ValueError("Invalid access code")
        
        # Validation: User not already enrolled
        if any(e.user == user for e in self.enrollments):
            raise ValueError(f"User {user.name} is already enrolled")
        
        # Validation: Check enrollment limit
        if not self.can_accept_students():
            raise ValueError(f"Course has reached maximum enrollment of {self.max_students}")
        
        enrollment = CourseEnrollment(
            id=uuid4(),
            user=user,
            role=UserRole.STUDENT
        )
        
        self.enrollments.append(enrollment)
        return enrollment
    
    def add_teacher(self, user: User) -> CourseEnrollment:
        """Add a teacher to the course"""
        if any(e.user == user for e in self.enrollments):
            raise ValueError(f"User {user.name} is already enrolled")
        
        enrollment = CourseEnrollment(
            id=uuid4(),
            user=user,
            role=UserRole.TEACHER
        )
        
        self.enrollments.append(enrollment)
        return enrollment
    
    def get_user_role(self, user: User) -> Optional[UserRole]:
        """Get the role of a user in this course"""
        for enrollment in self.enrollments:
            if enrollment.user == user:
                return enrollment.role
        return None
    
    def is_enrolled(self, user: User) -> bool:
        """Check if user is enrolled in course"""
        return any(e.user == user for e in self.enrollments)
    
    def post_announcement(self, user: User, title: str, content: str, 
                         visibility: ContentVisibility = ContentVisibility.ALL) -> Announcement:
        """Post an announcement (teachers only)"""
        role = self.get_user_role(user)
        if role != UserRole.TEACHER:
            raise ValueError("Only teachers can post announcements")
        
        announcement = Announcement(
            id=uuid4(),
            title=title,
            content=content,
            created_by=user,
            visibility=visibility
        )
        
        self.announcements.append(announcement)
        return announcement
    
    def add_material(self, user: User, title: str, description: str,
                    content_url: Optional[str] = None,
                    visibility: ContentVisibility = ContentVisibility.ALL) -> Material:
        """Add learning material (teachers only)"""
        role = self.get_user_role(user)
        if role != UserRole.TEACHER:
            raise ValueError("Only teachers can add materials")
        
        material = Material(
            id=uuid4(),
            title=title,
            description=description,
            content_url=content_url,
            created_by=user,
            visibility=visibility
        )
        
        self.materials.append(material)
        return material
    
    def get_visible_announcements(self, user: User) -> List[Announcement]:
        """Get announcements visible to user"""
        role = self.get_user_role(user)
        if not role:
            return []
        
        return [a for a in self.announcements if a.is_visible_to(role)]
    
    def get_visible_materials(self, user: User) -> List[Material]:
        """Get materials visible to user"""
        role = self.get_user_role(user)
        if not role:
            return []
        
        return [m for m in self.materials if m.is_visible_to(role)]
    
    def activate(self) -> None:
        """Activate the course"""
        if self.status == CourseStatus.ARCHIVED:
            raise ValueError("Cannot activate an archived course")
        self.status = CourseStatus.ACTIVE
    
    def archive(self) -> None:
        """Archive the course"""
        self.status = CourseStatus.ARCHIVED


@dataclass
class Assignment:
    """
    Aggregate Root representing an assignment.
    Contains deadline, submission rules, and grading information.
    """
    id: UUID
    course: Course
    title: str
    description: str
    created_by: User
    max_points: float
    due_date: datetime
    allow_late_submissions: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate that creator is a teacher in the course"""
        role = self.course.get_user_role(self.created_by)
        if role != UserRole.TEACHER:
            raise ValueError("Only teachers can create assignments")
    
    def is_past_due(self) -> bool:
        """Check if assignment is past due date"""
        return datetime.now() > self.due_date
    
    def can_submit(self, user: User) -> bool:
        """Check if user can submit for this assignment"""
        # Must be enrolled as student
        role = self.course.get_user_role(user)
        if role != UserRole.STUDENT:
            return False
        
        # If past due, check if late submissions allowed
        if self.is_past_due() and not self.allow_late_submissions:
            return False
        
        return True


@dataclass
class Submission:
    """
    Aggregate Root representing a student's submission for an assignment.
    Manages submission content, grading, and feedback.
    """
    id: UUID
    assignment: Assignment
    student: User
    content: str
    submitted_at: datetime
    status: SubmissionStatus = SubmissionStatus.SUBMITTED
    grade: Optional[Grade] = None
    feedback: Optional[str] = None
    
    @classmethod
    def create_submission(cls, assignment: Assignment, student: User, 
                         content: str) -> 'Submission':
        """
        Factory method to create a submission with validation.
        """
        # Validation: Student must be able to submit
        if not assignment.can_submit(student):
            raise ValueError(
                f"Student {student.name} cannot submit for this assignment"
            )
        
        # Determine status based on due date
        submitted_at = datetime.now()
        status = SubmissionStatus.SUBMITTED
        
        if submitted_at > assignment.due_date:
            status = SubmissionStatus.LATE
        
        return cls(
            id=uuid4(),
            assignment=assignment,
            student=student,
            content=content,
            submitted_at=submitted_at,
            status=status
        )
    
    def add_grade(self, graded_by: User, points: float, feedback: str = "") -> None:
        """
        Add grade and feedback to submission (teachers only).
        """
        # Validation: Only teachers can grade
        role = self.assignment.course.get_user_role(graded_by)
        if role != UserRole.TEACHER:
            raise ValueError("Only teachers can grade submissions")
        
        # Validation: Cannot grade own work (edge case)
        if graded_by == self.student:
            raise ValueError("Cannot grade own submission")
        
        # Create grade
        self.grade = Grade(points=points, max_points=self.assignment.max_points)
        self.feedback = feedback
        self.status = SubmissionStatus.GRADED
    
    def is_graded(self) -> bool:
        """Check if submission has been graded"""
        return self.status == SubmissionStatus.GRADED
    
    def is_late(self) -> bool:
        """Check if submission was late"""
        return self.status == SubmissionStatus.LATE or (
            self.submitted_at > self.assignment.due_date
        )


# ============================================================================
# DOMAIN SERVICES
# ============================================================================

class CourseManagementService:
    """Domain Service for course-related operations"""
    
    @staticmethod
    def bulk_enroll_students(course: Course, students: List[User], 
                           access_code: str) -> List[CourseEnrollment]:
        """Enroll multiple students at once"""
        enrollments = []
        failed = []
        
        for student in students:
            try:
                enrollment = course.enroll_student(student, access_code)
                enrollments.append(enrollment)
            except ValueError as e:
                failed.append((student, str(e)))
        
        if failed:
            print(f"Warning: {len(failed)} enrollments failed")
        
        return enrollments
    
    @staticmethod
    def get_course_statistics(course: Course) -> dict:
        """Get statistics about a course"""
        total_students = sum(1 for e in course.enrollments if e.is_student())
        total_teachers = sum(1 for e in course.enrollments if e.is_teacher())
        
        return {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_announcements": len(course.announcements),
            "total_materials": len(course.materials),
            "status": course.status.value,
            "enrollment_percentage": (
                (total_students / course.max_students * 100) 
                if course.max_students else None
            )
        }


class AssignmentService:
    """Domain Service for assignment-related operations"""
    
    @staticmethod
    def get_pending_submissions(assignment: Assignment, 
                               course: Course) -> List[User]:
        """Get list of students who haven't submitted"""
        # This would typically check against a submission repository
        # For now, returns enrolled students
        return [e.user for e in course.enrollments if e.is_student()]
    
    @staticmethod
    def calculate_average_grade(submissions: List[Submission]) -> Optional[float]:
        """Calculate average grade for graded submissions"""
        graded = [s for s in submissions if s.is_graded()]
        
        if not graded:
            return None
        
        total = sum(s.grade.percentage() for s in graded)
        return total / len(graded)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_usage():
    """Demonstrate the virtual classroom system"""
    
    # Create users
    teacher = User(uuid4(), "Prof. Miller", "miller@school.edu")
    student1 = User(uuid4(), "Alice Johnson", "alice@student.edu")
    student2 = User(uuid4(), "Bob Williams", "bob@student.edu")
    student3 = User(uuid4(), "Carol Davis", "carol@student.edu")
    
    # Create a course
    course = Course(
        id=uuid4(),
        name="Introduction to Python",
        description="Learn Python programming from scratch",
        created_by=teacher,
        access_code=AccessCode("PYTHON101"),
        max_students=2
    )
    
    print(f"[OK] Course created: '{course.name}'")
    print(f"  Access code: {course.access_code.value}")
    print(f"  Status: {course.status.value}")
    
    # Activate course
    course.activate()
    print("[OK] Course activated")
    
    # Students enroll
    enrollment1 = course.enroll_student(student1, "PYTHON101")
    print(f"[OK] {student1.name} enrolled as student")
    
    enrollment2 = course.enroll_student(student2, "PYTHON101")
    print(f"[OK] {student2.name} enrolled as student")
    
    # Try to enroll third student (should fail - max 2)
    try:
        course.enroll_student(student3, "PYTHON101")
    except ValueError as e:
        print(f"[ERROR] {student3.name} enrollment failed: {e}")
    
    # Teacher posts announcement
    announcement = course.post_announcement(
        teacher,
        "Welcome to the course!",
        "Looking forward to teaching you Python this semester."
    )
    print(f"[OK] Announcement posted: '{announcement.title}'")
    
    # Teacher adds material
    material = course.add_material(
        teacher,
        "Python Basics - Chapter 1",
        "Introduction to variables and data types",
        content_url="https://example.com/chapter1.pdf"
    )
    print(f"[OK] Material added: '{material.title}'")
    
    # Create assignment
    from datetime import timedelta
    assignment = Assignment(
        id=uuid4(),
        course=course,
        title="Homework 1: Variables and Types",
        description="Practice with Python variables",
        created_by=teacher,
        max_points=100,
        due_date=datetime.now() + timedelta(days=7)
    )
    print(f"[OK] Assignment created: '{assignment.title}'")
    print(f"  Due date: {assignment.due_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Max points: {assignment.max_points}")
    
    # Student submits work
    submission = Submission.create_submission(
        assignment,
        student1,
        "# My solution\nx = 5\ny = 10\nprint(x + y)"
    )
    print(f"[OK] {student1.name} submitted the assignment")
    print(f"  Status: {submission.status.value}")
    
    # Teacher grades submission
    submission.add_grade(
        teacher,
        points=95,
        feedback="Excellent work! Just remember to add comments."
    )
    print(f"[OK] Submission graded by {teacher.name}")
    print(f"  Grade: {submission.grade.points}/{submission.grade.max_points} ({submission.grade.percentage():.1f}%)")
    print(f"  Feedback: {submission.feedback}")
    
    # Get course statistics
    stats = CourseManagementService.get_course_statistics(course)
    print("\nCourse statistics:")
    print(f"  Students: {stats['total_students']}")
    print(f"  Teachers: {stats['total_teachers']}")
    print(f"  Announcements: {stats['total_announcements']}")
    print(f"  Materials: {stats['total_materials']}")
    print(f"  Enrollment: {stats['enrollment_percentage']:.0f}% full")


if __name__ == "__main__":
    example_usage()
