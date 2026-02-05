# Virtual Classroom System - Domain-Driven Design (DDD)

Virtual classroom similar to Google Classroom implemented with **Domain-Driven Design (DDD)**.

## Project Structure

```
classroom-ddd/
├── classroom_ddd.py          # Domain layer
├── classroom_application.py  # Application layer
└── README.md                 # Project documentation
```

## DDD Architecture

### Domain Model

```
Course (Aggregate Root)
  ├── enrollments: List[CourseEnrollment]
  ├── announcements: List[Announcement]
  ├── materials: List[Material]
  ├── access_code: AccessCode
  └── status: CourseStatus

Assignment (Aggregate Root)
  ├── course: Course
  ├── due_date: datetime
  ├── max_points: float
  └── allow_late_submissions: bool

Submission (Aggregate Root)
  ├── assignment: Assignment
  ├── student: User
  ├── grade: Grade
  └── status: SubmissionStatus
```

## DDD Concepts Implemented

### 1. Value Objects
- `AccessCode`: Course access code (minimum 6 characters)
- `Grade`: Score with points and percentage

### 2. Entities
- `User`: Person (teacher or student)
- `CourseEnrollment`: Enrollment with role
- `Announcement`: Course announcement
- `Material`: Learning material

### 3. Aggregates
- `Course`: Manages enrollments, content, and lifecycle
- `Assignment`: Manages tasks and deadlines
- `Submission`: Manages student work and grading

### 4. Domain Services
- `CourseManagementService`: Operations over courses
- `AssignmentService`: Operations for assignments

### 5. Repositories
- `ICourseRepository`, `IAssignmentRepository`, `ISubmissionRepository`
- In-memory implementations for testing

### 6. Use Cases
- `CreateCourseUseCase`: Create a course
- `EnrollStudentUseCase`: Enroll a student
- `CreateAssignmentUseCase`: Create an assignment
- `SubmitAssignmentUseCase`: Submit work
- `GradeSubmissionUseCase`: Grade a submission

## Operation Flow

### Example: Student submits an assignment

```
1. Use case receives request
2. Looks up Assignment and Student in repositories
3. Validates the student is allowed to submit
4. Creates Submission while enforcing deadlines
5. Persists the aggregate through the repository
```

## Business Rules

### Courses
- Only active courses accept enrollments
- Access code is required when joining
- Optional maximum number of students
- Only teachers can create content
- Content visibility is controlled by role
- States: DRAFT → ACTIVE → ARCHIVED

### Assignments
- Only teachers can create assignments
- Due date is mandatory
- Late submissions optional per assignment
- Maximum points defined up front

### Submissions
- Only students can submit work
- Deadline validation on each submission
- Automatic statuses: SUBMITTED or LATE
- Only teachers can grade
- Grade must stay within the allowed range
- One submission per student per assignment

### Access Control
- Users must be enrolled to see content
- Roles: TEACHER and STUDENT
- Permissions derived from role
- Content visibility configurable per item

## Using the System

### Basic Execution

```bash
# Run the domain demo
python classroom_ddd.py

# Run the demo with the application layer
python classroom_application.py
```

### Code Example

```python
from uuid import uuid4
from classroom_ddd import Course, User, AccessCode
from classroom_application import EnrollStudentUseCase

# Create a course
teacher = User(uuid4(), "Prof. Miller", "miller@school.edu")
course = Course(
    id=uuid4(),
    name="Python 101",
    description="Introduction to Python",
    created_by=teacher,
    access_code=AccessCode("PY101")
)
course.activate()

# Enroll a student
student = User(uuid4(), "Anna Lee", "anna@student.edu")
enrollment = course.enroll_student(student, "PY101")

print(f"{student.name} enrolled as {enrollment.role.value}")
```

## DDD Patterns Applied

| Pattern | Implementation | Purpose |
|--------|----------------|---------|
| **Aggregate Root** | `Course`, `Assignment`, `Submission` | Guarantees consistency |
| **Entity** | `User`, `Announcement`, `Material` | Objects with identity |
| **Value Object** | `AccessCode`, `Grade` | Immutable objects |
| **Repository** | `ICourseRepository`, etc. | Abstracts persistence |
| **Domain Service** | `CourseManagementService` | Operations across aggregates |
| **Use Case** | `CreateCourseUseCase` | Orchestrates operations |

## Architecture Benefits

### Expressive
- Code mirrors the education domain
- Explicit business rules
- Easy to reason about

### Testable
- Each layer isolated
- In-memory repositories
- Business rules separated from infrastructure

### Maintainable
- Infrastructure changes do not affect the domain
- New rules live in a single place
- Evolves naturally with the product

## Possible Extensions

- [ ] Notification system
- [ ] Assignment calendar
- [ ] Discussion forum
- [ ] Quizzes and exams
- [ ] Performance analytics
- [ ] Google Drive integration
- [ ] Badges or achievements
- [ ] Video conferencing

## Differences Compared to the Library System

This system is simpler and more direct than the library system:

**Similarities**
- Well defined aggregates
- Clear separation of layers
- Business rule validation
- Repository pattern

**Differences**
- Fewer entities
- Simpler rules
- Single permission level (TEACHER/STUDENT)
- No reservation workflow
- No automatic penalties

---

**System designed following Domain-Driven Design principles**
