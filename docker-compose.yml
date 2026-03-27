version: "3.9"

services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ${DB_NAME:-mailwave}
      POSTGRES_USER: ${DB_USER:-mailwave}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-mailwave_secret}
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-mailwave}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    command: >
      sh -c "python manage.py migrate --noinput &&
             python manage.py collectstatic --noinput &&
             gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 2"
    volumes:
      - ./backend:/app
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    env_file:
      - .env
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8000:8000"

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    command: celery -A config worker -l info --concurrency=4
    volumes:
      - ./backend:/app
    env_file:
      - .env
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      backend:
        condition: service_started

  celery_beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - ./backend:/app
    env_file:
      - .env
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      backend:
        condition: service_started

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    restart: unless-stopped
    volumes:
      - frontend_build:/app/build
    depends_on:
      - backend

  nginx:
    image: nginx:1.25-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf
      - static_volume:/app/staticfiles
      - media_volume:/app/media
      - frontend_build:/usr/share/nginx/html
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
  frontend_build:
