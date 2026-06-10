# Procfile — tells the platform how to run your app
# Web server: Gunicorn with 4 workers
web: gunicorn onistuka.wsgi:application --workers 4 --threads 2 --bind 0.0.0.0:$PORT --log-level info --access-logfile - --error-logfile -

# Release command: runs migrations automatically on each deploy
release: python manage.py migrate --noinput
