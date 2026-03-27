# MailWave - Email Marketing Platform

A production-grade email marketing platform with campaign builder, contact management, segmentation, A/B testing, scheduling, analytics, templates, automation sequences, and unsubscribe management.

## Tech Stack

- **Backend:** Django 5.x + Django REST Framework
- **Frontend:** React 18 + Redux Toolkit
- **Database:** PostgreSQL 16
- **Cache & Broker:** Redis 7
- **Task Queue:** Celery 5
- **Reverse Proxy:** Nginx
- **Containerization:** Docker + Docker Compose

## Features

- **Campaign Builder:** Create, schedule, and send email campaigns with a visual editor
- **Contact Management:** Import, organize, and manage subscriber lists
- **Segmentation:** Build dynamic segments with rule-based filtering
- **A/B Testing:** Split test subject lines, content, and send times
- **Automation Sequences:** Build multi-step drip campaigns with triggers and delays
- **Analytics Dashboard:** Track open rates, click rates, bounces, and unsubscribes in real time
- **Template Gallery:** Pre-built and custom email templates with drag-and-drop editing
- **Unsubscribe Management:** One-click unsubscribe with preference center

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/mailwave.git
   cd mailwave
   ```

2. Copy environment variables:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` with your configuration (database credentials, email provider keys, etc.)

4. Build and start all services:
   ```bash
   docker-compose up --build
   ```

5. Run database migrations:
   ```bash
   docker-compose exec backend python manage.py migrate
   ```

6. Create a superuser:
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```

7. Access the application:
   - Frontend: http://localhost
   - Backend API: http://localhost/api/
   - Admin Panel: http://localhost/admin/
   - API Documentation: http://localhost/api/docs/

## Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm start
```

### Running Celery Workers

```bash
cd backend
celery -A config worker -l info
celery -A config beat -l info
```

## API Endpoints

### Authentication
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login and obtain JWT tokens
- `POST /api/auth/refresh/` - Refresh JWT token
- `GET /api/auth/me/` - Get current user profile

### Contacts
- `GET /api/contacts/` - List contacts
- `POST /api/contacts/` - Create contact
- `GET /api/contacts/lists/` - List contact lists
- `POST /api/contacts/lists/` - Create contact list
- `GET /api/contacts/segments/` - List segments
- `POST /api/contacts/segments/` - Create segment

### Campaigns
- `GET /api/campaigns/` - List campaigns
- `POST /api/campaigns/` - Create campaign
- `POST /api/campaigns/{id}/send/` - Send campaign
- `POST /api/campaigns/{id}/schedule/` - Schedule campaign
- `GET /api/campaigns/{id}/stats/` - Campaign statistics

### Templates
- `GET /api/templates/` - List templates
- `POST /api/templates/` - Create template

### Automation
- `GET /api/automation/sequences/` - List automation sequences
- `POST /api/automation/sequences/` - Create sequence
- `POST /api/automation/sequences/{id}/activate/` - Activate sequence

### Analytics
- `GET /api/analytics/dashboard/` - Dashboard overview
- `GET /api/analytics/campaigns/{id}/` - Campaign analytics
- `GET /api/analytics/engagement/` - Engagement metrics

## Project Structure

```
mailwave/
├── backend/
│   ├── apps/
│   │   ├── accounts/       # User & organization management
│   │   ├── contacts/       # Contact lists & segmentation
│   │   ├── campaigns/      # Campaign builder & scheduling
│   │   ├── email_templates/# Email template management
│   │   ├── automation/     # Automation sequences
│   │   └── analytics/      # Tracking & reporting
│   ├── config/             # Django settings & configuration
│   ├── utils/              # Shared utilities
│   └── manage.py
├── frontend/
│   ├── public/
│   └── src/
│       ├── api/            # API client modules
│       ├── components/     # React components
│       ├── pages/          # Page components
│       ├── store/          # Redux store & slices
│       ├── hooks/          # Custom React hooks
│       └── styles/         # Global styles
├── nginx/                  # Nginx configuration
├── docker-compose.yml
└── .env.example
```

## Environment Variables

See `.env.example` for all available configuration options.

## License

MIT License. See LICENSE for details.
