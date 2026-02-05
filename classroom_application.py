"""
Virtual Classroom System - Application Layer and Repositories
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from classroom_ddd import (
    Course, Assignment, Submission, User,
    CourseEnrollment, Announcement, Material,
    CourseStatus, UserRole, SubmissionStatus,
    CourseManagementService, AssignmentService
)


# ============================================================================
# REPOSITORY INTERFACES
# ============================================================================

class ICourseRepository(ABC):
    """Repository interface for Course aggregate"""
    
    @abstractmethod
    def find_by_id(self, course_id: UUID) -> Optional[Course]:
        pass
    
    @abstractmethod
    def find_by_access_code(self, code: str) -> Optional[Course]:
        pass
    
    @abstractmethod
    def find_active_courses(self) -> List[Course]:
        pass
    
    @abstractmethod
    def find_by_teacher(self, teacher_id: UUID) -> List[Course]:
        pass
    
    @abstractmethod
    def save(self, course: Course) -> None:
        pass


class IAssignmentRepository(ABC):
    """Repository interface for Assignment aggregate"""
    
    @abstractmethod
    def find_by_id(self, assignment_id: UUID) -> Optional[Assignment]:
        pass
    
    @abstractmethod
    def find_by_course(self, course_id: UUID) -> List[Assignment]:
        pass
    
    @abstractmethod
    def find_upcoming(self, course_id: UUID) -> List[Assignment]:
        pass
    
    @abstractmethod
    def save(self, assignment: Assignment) -> None:
        pass


class ISubmissionRepository(ABC):
    """Repository interface for Submission aggregate"""
    
    @abstractmethod
    def find_by_id(self, submission_id: UUID) -> Optional[Submission]:
        pass
    
    @abstractmethod
    def find_by_assignment(self, assignment_id: UUID) -> List[Submission]:
        pass
    
    @abstractmethod
    def find_by_student(self, student_id: UUID, assignment_id: UUID) -> Optional[Submission]:
        pass
    
    @abstractmethod
    def find_ungraded(self, assignment_id: UUID) -> List[Submission]:
        pass
    
    @abstractmethod
    def save(self, submission: Submission) -> None:
        pass


class IUserRepository(ABC):
    """Repository interface for User entity"""
    
    @abstractmethod
    def find_by_id(self, user_id: UUID) -> Optional[User]:
        pass
    
    @abstractmethod
    def find_by_email(self, email: str) -> Optional[User]:
        pass
    
    @abstractmethod
    def save(self, user: User) -> None:
        pass


# ============================================================================
# IN-MEMORY REPOSITORY IMPLEMENTATIONS
# ============================================================================

class InMemoryCourseRepository(ICourseRepository):
    
    def __init__(self):
        self._courses: dict[UUID, Course] = {}
    
    def find_by_id(self, course_id: UUID) -> Optional[Course]:
        return self._courses.get(course_id)
    
    def find_by_access_code(self, code: str) -> Optional[Course]:
        for course in self._courses.values():
            if course.access_code.value == code:
                return course
        return None
    
    def find_active_courses(self) -> List[Course]:
        return [c for c in self._courses.values() if c.is_active()]
    
    def find_by_teacher(self, teacher_id: UUID) -> List[Course]:
        return [
            c for c in self._courses.values()
            if any(e.user.id == teacher_id and e.is_teacher() 
                  for e in c.enrollments)
        ]
    
    def save(self, course: Course) -> None:
        self._courses[course.id] = course


class InMemoryAssignmentRepository(IAssignmentRepository):
    
    def __init__(self):
        self._assignments: dict[UUID, Assignment] = {}
    
    def find_by_id(self, assignment_id: UUID) -> Optional[Assignment]:
        return self._assignments.get(assignment_id)
    
    def find_by_course(self, course_id: UUID) -> List[Assignment]:
        return [
            a for a in self._assignments.values()
            if a.course.id == course_id
        ]
    
    def find_upcoming(self, course_id: UUID) -> List[Assignment]:
        now = datetime.now()
        return [
            a for a in self._assignments.values()
            if a.course.id == course_id and a.due_date > now
        ]
    
    def save(self, assignment: Assignment) -> None:
        self._assignments[assignment.id] = assignment


class InMemorySubmissionRepository(ISubmissionRepository):
    
    def __init__(self):
        self._submissions: dict[UUID, Submission] = {}
    
    def find_by_id(self, submission_id: UUID) -> Optional[Submission]:
        return self._submissions.get(submission_id)
    
    def find_by_assignment(self, assignment_id: UUID) -> List[Submission]:
        return [
            s for s in self._submissions.values()
            if s.assignment.id == assignment_id
        ]
    
    def find_by_student(self, student_id: UUID, assignment_id: UUID) -> Optional[Submission]:
        for submission in self._submissions.values():
            if (submission.student.id == student_id and 
                submission.assignment.id == assignment_id):
                return submission
        return None
    
    def find_ungraded(self, assignment_id: UUID) -> List[Submission]:
        return [
            s for s in self._submissions.values()
            if s.assignment.id == assignment_id and not s.is_graded()
        ]
    
    def save(self, submission: Submission) -> None:
        self._submissions[submission.id] = submission


class InMemoryUserRepository(IUserRepository):
    
    def __init__(self):
        self._users: dict[UUID, User] = {}
    
    def find_by_id(self, user_id: UUID) -> Optional[User]:
        return self._users.get(user_id)
    
    def find_by_email(self, email: str) -> Optional[User]:
        for user in self._users.values():
            if user.email == email:
                return user
        return None
    
    def save(self, user: User) -> None:
        self._users[user.id] = user


# ============================================================================
# APPLICATION SERVICES (Use Cases)
# ============================================================================

class CreateCourseUseCase:
    """Application service for creating a course"""
    
    def __init__(
        self,
        course_repo: ICourseRepository,
        user_repo: IUserRepository
    ):
        self.course_repo = course_repo
        self.user_repo = user_repo
    
    def execute(self, teacher_id: UUID, name: str, description: str,
                access_code: str, max_students: Optional[int] = None) -> Course:
        """Create a new course"""
        from classroom_ddd import AccessCode
        
        # Find teacher
        teacher = self.user_repo.find_by_id(teacher_id)
        if not teacher:
            raise ValueError(f"Teacher {teacher_id} not found")
        
        # Create course
        course = Course(
            id=UUID(int=0).hex,  # Will be replaced
            name=name,
            description=description,
            created_by=teacher,
            access_code=AccessCode(access_code),
            max_students=max_students
        )
        course.id = UUID(int=hash(course.name + teacher.email) % (2**128))
        
        # Persist
        self.course_repo.save(course)
        
        return course


class EnrollStudentUseCase:
    """Application service for enrolling students"""
    
    def __init__(
        self,
        course_repo: ICourseRepository,
        user_repo: IUserRepository
    ):
        self.course_repo = course_repo
        self.user_repo = user_repo
    
    def execute(self, student_id: UUID, access_code: str) -> CourseEnrollment:
        """Enroll a student in a course"""
        
        # Find student
        student = self.user_repo.find_by_id(student_id)
        if not student:
            raise ValueError(f"Student {student_id} not found")
        
        # Find course by access code
        course = self.course_repo.find_by_access_code(access_code)
        if not course:
            raise ValueError(f"Course with code {access_code} not found")
        
        # Enroll student (domain handles validation)
        enrollment = course.enroll_student(student, access_code)
        
        # Persist
        self.course_repo.save(course)
        
        return enrollment


class CreateAssignmentUseCase:
    """Application service for creating assignments"""
    
    def __init__(
        self,
        course_repo: ICourseRepository,
        assignment_repo: IAssignmentRepository,
        user_repo: IUserRepository
    ):
        self.course_repo = course_repo
        self.assignment_repo = assignment_repo
        self.user_repo = user_repo
    
    def execute(self, course_id: UUID, teacher_id: UUID,
                title: str, description: str, max_points: float,
                due_date: datetime, allow_late: bool = False) -> Assignment:
        """Create a new assignment"""
        
        # Find course
        course = self.course_repo.find_by_id(course_id)
        if not course:
            raise ValueError(f"Course {course_id} not found")
        
        # Find teacher
        teacher = self.user_repo.find_by_id(teacher_id)
        if not teacher:
            raise ValueError(f"Teacher {teacher_id} not found")
        
        # Create assignment (domain validates teacher role)
        assignment = Assignment(
            id=UUID(int=0).hex,
            course=course,
            title=title,
            description=description,
            created_by=teacher,
            max_points=max_points,
            due_date=due_date,
            allow_late_submissions=allow_late
        )
        assignment.id = UUID(int=hash(title + str(course_id)) % (2**128))
        
        # Persist
        self.assignment_repo.save(assignment)
        
        return assignment


class SubmitAssignmentUseCase:
    """Application service for submitting assignments"""
    
    def __init__(
        self,
        assignment_repo: IAssignmentRepository,
        submission_repo: ISubmissionRepository,
        user_repo: IUserRepository
    ):
        self.assignment_repo = assignment_repo
        self.submission_repo = submission_repo
        self.user_repo = user_repo
    
    def execute(self, assignment_id: UUID, student_id: UUID,
                content: str) -> Submission:
        """Submit work for an assignment"""
        
        # Find assignment
        assignment = self.assignment_repo.find_by_id(assignment_id)
        if not assignment:
            raise ValueError(f"Assignment {assignment_id} not found")
        
        # Find student
        student = self.user_repo.find_by_id(student_id)
        if not student:
            raise ValueError(f"Student {student_id} not found")
        
        # Check if already submitted
        existing = self.submission_repo.find_by_student(student_id, assignment_id)
        if existing:
            raise ValueError("Assignment already submitted")
        
        # Create submission (domain handles validation)
        submission = Submission.create_submission(assignment, student, content)
        
        # Persist
        self.submission_repo.save(submission)
        
        return submission


class GradeSubmissionUseCase:
    """Application service for grading submissions"""
    
    def __init__(
        self,
        submission_repo: ISubmissionRepository,
        user_repo: IUserRepository
    ):
        self.submission_repo = submission_repo
        self.user_repo = user_repo
    
    def execute(self, submission_id: UUID, teacher_id: UUID,
                points: float, feedback: str = "") -> Submission:
        """Grade a student's submission"""
        
        # Find submission
        submission = self.submission_repo.find_by_id(submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        # Find teacher
        teacher = self.user_repo.find_by_id(teacher_id)
        if not teacher:
            raise ValueError(f"Teacher {teacher_id} not found")
        
        # Add grade (domain handles validation)
        submission.add_grade(teacher, points, feedback)
        
        # Persist
        self.submission_repo.save(submission)
        
        return submission


# ============================================================================
# DEMO WITH APPLICATION LAYER
# ============================================================================

def demo_with_application_layer():
    """Demonstrate the complete DDD architecture"""
    from uuid import uuid4
    from datetime import timedelta
    from classroom_ddd import User
    
    # Setup repositories
    user_repo = InMemoryUserRepository()
    course_repo = InMemoryCourseRepository()
    assignment_repo = InMemoryAssignmentRepository()
    submission_repo = InMemorySubmissionRepository()
    
    # Setup use cases
    create_course = CreateCourseUseCase(course_repo, user_repo)
    enroll_student = EnrollStudentUseCase(course_repo, user_repo)
    create_assignment = CreateAssignmentUseCase(course_repo, assignment_repo, user_repo)
    submit_assignment = SubmitAssignmentUseCase(assignment_repo, submission_repo, user_repo)
    grade_submission = GradeSubmissionUseCase(submission_repo, user_repo)
    
    # Create test data
    teacher = User(uuid4(), "Dr. Smith", "smith@school.edu")
    student1 = User(uuid4(), "Alice Johnson", "alice@student.edu")
    student2 = User(uuid4(), "Bob Williams", "bob@student.edu")
    
    user_repo.save(teacher)
    user_repo.save(student1)
    user_repo.save(student2)
    
    print("=== Virtual Classroom Demo ===\n")
    
    # USE CASE 1: Create course
    print("1. Creating course...")
    course = create_course.execute(
        teacher.id,
        "Web Development 101",
        "Learn HTML, CSS, and JavaScript",
        "WEB101",
        max_students=20
    )
    print(f"   ✓ Course created: '{course.name}'")
    print(f"   Access code: {course.access_code.value}\n")
    
    # Activate course
    course.activate()
    course_repo.save(course)
    
    # USE CASE 2: Enroll students
    print("2. Enrolling students...")
    enrollment1 = enroll_student.execute(student1.id, "WEB101")
    print(f"   ✓ {student1.name} enrolled")
    
    enrollment2 = enroll_student.execute(student2.id, "WEB101")
    print(f"   ✓ {student2.name} enrolled\n")
    
    # USE CASE 3: Create assignment
    print("3. Creating assignment...")
    assignment = create_assignment.execute(
        course.id,
        teacher.id,
        "HTML Basics",
        "Create a simple HTML page",
        max_points=100,
        due_date=datetime.now() + timedelta(days=3)
    )
    print(f"   ✓ Assignment created: '{assignment.title}'")
    print(f"   Due: {assignment.due_date.strftime('%Y-%m-%d')}\n")
    
    # USE CASE 4: Submit assignment
    print("4. Student submitting work...")
    submission = submit_assignment.execute(
        assignment.id,
        student1.id,
        "<html><body><h1>Hello World</h1></body></html>"
    )
    print(f"   ✓ {student1.name} submitted assignment")
    print(f"   Status: {submission.status.value}\n")
    
    # USE CASE 5: Grade submission
    print("5. Teacher grading submission...")
    graded = grade_submission.execute(
        submission.id,
        teacher.id,
        points=95,
        feedback="Great work! Add some CSS next time."
    )
    print(f"   ✓ Graded by {teacher.name}")
    print(f"   Grade: {graded.grade.percentage():.1f}%")
    print(f"   Feedback: {graded.feedback}\n")
    
    print("=== Demo Complete ===")


if __name__ == "__main__":
    demo_with_application_layer()
