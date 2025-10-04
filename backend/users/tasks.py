import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import User, UserOtp
from .utils import generate_otp

from_email = settings.EMAIL_HOST_USER
logger = logging.getLogger(__name__)


@shared_task
def send_otp_to_user_mail(email):
    """Send otp to user email"""
    if User.objects.filter(email=email).exists():
        subject = "Your OTP Code"
        template = "mails/otp.html"

        otp = generate_otp()
        user_otp, created = UserOtp.objects.update_or_create(
            email=email, defaults={"otp": otp}
        )

        if not created:
            user_otp.otp = otp
            user_otp.save()

        html_message = render_to_string(
            template,
            {
                "message": user_otp.otp,
                "backend_url": f"{settings.BACKEND_URL}",
            },
        )
        send_mail(
            subject,
            html_message,
            from_email,
            [email],
            fail_silently=False,
        )
        delete_user_otp.apply_async(args=[email], countdown=120)


@shared_task
def delete_user_otp(email):
    """Delete userotp using email"""
    try:
        UserOtp.objects.get(email=email).delete()
    except UserOtp.DoesNotExist:
        pass
