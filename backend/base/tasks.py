from core.celery import app
from django.core import management


@app.task
def session_cleanup():
    """
    Does cleanup jobs like clearing the sessions table
    """
    management.call_command("clearsessions", verbosity=0)
