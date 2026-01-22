# ReportCardApp: Multi-Tenant Report Card System

A mobile-first, offline-capable school management system for generating report cards with multi-tenant architecture.

## Features
- **Multi-Tenant**: Each school operates in complete isolation
- **Offline-First**: Full functionality without internet connection
- **Manual Sync**: Explicit control over data synchronization
- **Configurable Grading**: Customizable report cards per school
- **PDF Export**: Generate and share report cards offline
- **Role-Based Access**: Admin, Teacher, Student roles
- **Progressive Web App**: Installable on mobile devices with native-like experience

## Tech Stack
### Mobile Experience
- Progressive Web App (PWA) with Service Worker
- Installable on iOS/Android home screens
- Full offline capability with background sync
- Touch-optimized responsive interface

### Web App
- Django Templates with Bootstrap
- PWA manifest and service worker for mobile installation
- Responsive design for all screen sizes
- Single codebase for web and mobile

### Backend
- Django + Django REST Framework
- PostgreSQL (PythonAnywhere)
- JWT Authentication for API, Django sessions for web

## Getting Started

### Development Setup
1. Install Python 3.8+
2. Clone the repository
3. Create virtual environment: `python -m venv venv`
4. Activate venv: `venv\Scripts\activate` (Windows)
5. Install dependencies: `pip install -r requirements.txt`
6. Run migrations: `python manage.py migrate`
7. Run server: `python manage.py runserver`

### API Endpoints
- POST /api/token/ - Obtain JWT token
- POST /api/token/refresh/ - Refresh JWT token
- GET /api/sync/?last_sync=ISO_DATE - Sync data since timestamp
- /api/schools/ - School management
- /api/users/ - User management
- /api/class-sections/ - Class/Section management
- /api/subjects/ - Subject management
- /api/grading-scales/ - Grading scale management
- /api/student-enrollments/ - Student enrollment management

Use `School-ID` header for multi-tenancy.

## Deployment to PythonAnywhere
1. Create PythonAnywhere account
2. Upload code to PythonAnywhere
3. Set environment variables: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
4. Install requirements
5. Run migrations
6. Configure WSGI file

## Architecture
Multi-tenant Django REST API with JWT authentication and offline sync support.

Super admin can manage schools, users, classes, subjects, grading scales, and student enrollments, school themes and report card templates.
