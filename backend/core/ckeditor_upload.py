from django.conf import settings
from django.utils.translation import gettext as _
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from django_ckeditor_5.forms import UploadFileForm
from django_ckeditor_5.permissions import check_upload_permission
from django_ckeditor_5.views import handle_uploaded_file, NoImageException, image_verify


@require_POST
@check_upload_permission
def upload_file(request):
    form = UploadFileForm(request.POST, request.FILES)
    allow_all_file_types = getattr(settings, "CKEDITOR_5_ALLOW_ALL_FILE_TYPES", False)

    if not allow_all_file_types:
        try:
            image_verify(request.FILES["upload"])
        except NoImageException as ex:
            return JsonResponse({"error": {"message": f"{ex}"}}, status=400)

    if form.is_valid():
        # Get the file path from the handler
        file_path = handle_uploaded_file(request.FILES["upload"])

        # Prepend the domain name to the file path
        full_url = f"{settings.BACKEND_URL}{file_path}"
        return JsonResponse({"url": full_url})

    if form.errors["upload"]:
        return JsonResponse(
            {"error": {"message": form.errors["upload"][0]}},
            status=400,
        )

    return JsonResponse({"error": {"message": _("Invalid form data")}}, status=400)
