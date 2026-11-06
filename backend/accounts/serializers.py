from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from base import names
from base.serializers import ModelSerializer
from wallet.services import open_wallet
from .models import LoginPageLabel, User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "email", "display_name", "password"]
        # The email is also the username (150 max). validate_email checks uniqueness in any letter case.
        extra_kwargs = {"email": {"max_length": 150, "validators": []}}

    def validate_email(self, value):
        email = value.lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A player with this email already exists.", code="email_taken")
        return email

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            display_name=validated_data.get("display_name", ""),
        )
        open_wallet(user)
        return user


class MeSerializer(serializers.ModelSerializer):
    public_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "display_name", "public_id", "date_joined"]

    def get_public_id(self, obj):
        """How other players' screens tell this player apart (a roulette seat is `player-<public_id>`)."""
        return names.public_id(obj.pk)


class LoginPageLabelSerializer(ModelSerializer):
    class Meta:
        model = LoginPageLabel
        fields = "__all__"
