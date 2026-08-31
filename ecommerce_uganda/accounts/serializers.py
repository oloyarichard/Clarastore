from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, District


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ['id', 'name', 'type', 'forwarding_hub']


class UserSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source='district.name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'role', 'district', 'district_name', 'date_joined']
        read_only_fields = ['role', 'date_joined']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    district = serializers.PrimaryKeyRelatedField(queryset=District.objects.all(), required=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'first_name', 'last_name', 'phone', 'district']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        validated_data['role'] = 'customer'
        # username isn't part of the product's signup flow (email/password
        # only) but AbstractUser still requires one internally — derive it
        # from the email so the API surface stays email-only.
        validated_data['username'] = self._generate_username(validated_data['email'])
        user = User.objects.create_user(**validated_data)
        return user

    @staticmethod
    def _generate_username(email):
        base = email.split('@')[0][:25]
        candidate = base
        i = 1
        while User.objects.filter(username=candidate).exists():
            candidate = f"{base}{i}"
            i += 1
        return candidate


class AgentCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'phone', 'district']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        validated_data['role'] = 'agent'
        validated_data['username'] = UserRegistrationSerializer._generate_username(validated_data['email'])
        user = User.objects.create_user(**validated_data)
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    # Deliberately no validate_email existence check here — unlike
    # registration's email-already-exists check, confirming or denying
    # whether an email has an account is exactly the kind of thing a
    # password reset endpoint must never leak. The view always returns
    # the same generic response regardless of whether a match was found.


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value
