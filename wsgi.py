"""WSGI entrypoint for deployment servers (gunicorn, uwsgi, etc.)"""

from app import app

# When using gunicorn: `gunicorn wsgi:app`
# The application object imported above will be exposed as "app".

if __name__ == '__main__':
    # allow running directly (for quick tests only)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))