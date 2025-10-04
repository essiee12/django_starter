from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from users.models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("full_name", "email")

    def __init__(self, *args, **kwargs):
        super(CustomUserCreationForm, self).__init__(*args, **kwargs) # pragma: no cover

        for field in self.fields:

            self.fields[field].widget.attrs.update(
                {
                    "class": "form-control",
                    "placeholder": self.fields[field].label,
                }
            )


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = (
            "email",
            "full_name",
            "password",
        )
