import unittest
from datetime import datetime, timedelta
from uuid import uuid4

from classroom_ddd import (
    AccessCode,
    Assignment,
    Course,
    CourseManagementService,
    Submission,
    SubmissionStatus,
    User,
    UserRole,
)


class VirtualClassroomTests(unittest.TestCase):
    def setUp(self):
        self.teacher = User(uuid4(), "Dr. Taylor", "taylor@school.edu")
        self.student = User(uuid4(), "Sam Parker", "sam@student.edu")
        self.other_student = User(uuid4(), "Jamie Stone", "jamie@student.edu")
        self.course = Course(
            id=uuid4(),
            name="Software Engineering",
            description="Domain-Driven Design in practice",
            created_by=self.teacher,
            access_code=AccessCode("ENG123"),
            max_students=1,
        )
        self.course.activate()

    def test_teacher_is_enrolled_on_course_creation(self):
        role = self.course.get_user_role(self.teacher)
        self.assertEqual(role, UserRole.TEACHER)

    def test_student_enrollment_requires_valid_code(self):
        enrollment = self.course.enroll_student(self.student, "ENG123")
        self.assertEqual(enrollment.role, UserRole.STUDENT)
        with self.assertRaises(ValueError):
            self.course.enroll_student(self.other_student, "WRONG")

    def test_cannot_exceed_maximum_enrollment(self):
        self.course.enroll_student(self.student, "ENG123")
        with self.assertRaises(ValueError):
            self.course.enroll_student(self.other_student, "ENG123")

    def test_assignment_must_be_created_by_teacher(self):
        self.course.enroll_student(self.student, "ENG123")
        due_date = datetime.now() + timedelta(days=1)
        assignment = Assignment(
            id=uuid4(),
            course=self.course,
            title="Modeling",
            description="Create the aggregates",
            created_by=self.teacher,
            max_points=100,
            due_date=due_date,
        )
        self.assertEqual(assignment.created_by, self.teacher)
        with self.assertRaises(ValueError):
            Assignment(
                id=uuid4(),
                course=self.course,
                title="Unauthorized Task",
                description="Students cannot create assignments",
                created_by=self.student,
                max_points=5,
                due_date=due_date,
            )

    def test_submission_respects_deadlines(self):
        late_assignment = Assignment(
            id=uuid4(),
            course=self.course,
            title="Async Exercise",
            description="Explain the event loop",
            created_by=self.teacher,
            max_points=20,
            due_date=datetime.now() - timedelta(days=1),
            allow_late_submissions=True,
        )
        self.course.enroll_student(self.student, "ENG123")
        submission = Submission.create_submission(
            late_assignment, self.student, "Late but allowed"
        )
        self.assertEqual(submission.status, SubmissionStatus.LATE)
        assignment_no_late = Assignment(
            id=uuid4(),
            course=self.course,
            title="No late submissions",
            description="Must be on time",
            created_by=self.teacher,
            max_points=10,
            due_date=datetime.now() - timedelta(days=1),
            allow_late_submissions=False,
        )
        with self.assertRaises(ValueError):
            Submission.create_submission(
                assignment_no_late, self.student, "Should raise because late"
            )

    def test_grading_requires_teacher(self):
        assignment = Assignment(
            id=uuid4(),
            course=self.course,
            title="Repositories",
            description="Describe persistence boundaries",
            created_by=self.teacher,
            max_points=50,
            due_date=datetime.now() + timedelta(days=1),
        )
        self.course.enroll_student(self.student, "ENG123")
        submission = Submission.create_submission(
            assignment, self.student, "Repository pattern write-up"
        )
        submission.add_grade(self.teacher, 40, "Solid explanation")
        self.assertTrue(submission.is_graded())
        self.assertEqual(submission.grade.points, 40)
        with self.assertRaises(ValueError):
            submission.add_grade(self.student, 50)

    def test_course_statistics_include_counts(self):
        self.course.enroll_student(self.student, "ENG123")
        stats = CourseManagementService.get_course_statistics(self.course)
        self.assertEqual(stats["total_students"], 1)
        self.assertEqual(stats["total_teachers"], 1)
        self.assertEqual(stats["status"], "active")


if __name__ == "__main__":
    unittest.main()
