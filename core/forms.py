from django.contrib.auth.forms import AuthenticationForm
from django import forms
from .models import HospitalUser

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )



class HospitalUserLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Mobile Number",
        widget=forms.TextInput(attrs={'autofocus': True, 'placeholder': 'Enter mobile number', 'class': 'form-control'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter password', 'class': 'form-control'})
    )




class ProfileForm(forms.ModelForm):
    class Meta:
        model = HospitalUser
        fields = ['display_name']
        widgets = {
            'display_name': forms.TextInput(attrs={'class': 'form-control'}),
        }    # you can add other editable fields here, e.g. email, password, etc.
