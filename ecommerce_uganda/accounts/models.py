from django.contrib.auth.models import AbstractUser
from django.db import models


class District(models.Model):
    DISTRICT_TYPE_CHOICES = [
        ('hub', 'Hub'),
        ('sub', 'Sub'),
    ]

    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=10, choices=DISTRICT_TYPE_CHOICES, default='sub')
    forwarding_hub = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_districts',
        limit_choices_to={'type': 'hub'},
        help_text="Which hub forwards to this district. Only applicable for sub-districts."
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.type})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.type == 'hub' and self.forwarding_hub is not None:
            raise ValidationError("Hub districts cannot have a forwarding hub.")
        if self.type == 'sub' and self.forwarding_hub is None:
            raise ValidationError("Sub-districts must have a forwarding hub.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class User(AbstractUser):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('agent', 'Agent'),
        ('admin', 'Admin'),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer')
    phone = models.CharField(max_length=20, blank=True)
    district = models.ForeignKey(
        District,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )

    # Login is by email, per the product decision (email + password auth).
    # 'username' is still required by AbstractUser/createsuperuser, but is
    # no longer what customers/agents actually log in with.
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def is_customer(self):
        return self.role == 'customer'

    @property
    def is_agent(self):
        return self.role == 'agent'

    @property
    def is_admin_role(self):
        return self.role == 'admin'
