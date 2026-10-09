from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Order, phone_validator, postal_validator

User = get_user_model()


class RegisterForm(UserCreationForm):
    full_name = forms.CharField(max_length=150, label="Full name")
    email = forms.EmailField(label="Email address")

    class Meta:
        model = User
        fields = ("full_name", "username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        parts = self.cleaned_data["full_name"].strip().split(None, 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ""
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username", widget=forms.TextInput(attrs={"autofocus": True}))


class CheckoutForm(forms.ModelForm):
    full_name = forms.CharField(max_length=150, label="Full name")
    phone = forms.CharField(max_length=20, validators=[phone_validator], label="Phone number")
    shipping_address = forms.CharField(
        label="Shipping address", widget=forms.Textarea(attrs={"rows": 3})
    )
    postal_code = forms.CharField(max_length=10, validators=[postal_validator], label="Postal code")

    class Meta:
        model = Order
        fields = ["full_name", "email", "phone", "shipping_address", "city", "state", "postal_code"]
        labels = {"email": "Email address", "city": "City", "state": "State"}

    def clean_full_name(self):
        name = self.cleaned_data["full_name"].strip()
        if len(name) < 3:
            raise forms.ValidationError("Please enter your full name.")
        return name

    def clean_shipping_address(self):
        addr = self.cleaned_data["shipping_address"].strip()
        if len(addr) < 8:
            raise forms.ValidationError("Please enter a complete shipping address.")
        return addr


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, label="Your name")
    email = forms.EmailField(label="Email address")
    subject = forms.CharField(max_length=150)
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}))
