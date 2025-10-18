from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class MaterialRecovery(models.Model):
    material = models.CharField(max_length=20, default=None)
    recovery_rate = models.CharField(max_length=3, default=None)  
    min_market_price = models.CharField(max_length=10, default=None)  
    max_market_price = models.CharField(max_length=10, default=None) 

    def __str__(self):
        return self.material

class InspectionType(models.Model):
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name

class ThermalRiskInspection(models.Model):
    RISK_TYPES = [
        ("Critical Overheating", "Critical Overheating"),
        ("Excessive Heating", "Excessive Heating"),
        ("Unusual Cooling", "Unusual Cooling"),
        ("Panel/Sensor Unresponsive", "Panel/Sensor Unresponsive"),
    ]

    risk_type = models.CharField(max_length=100, choices=RISK_TYPES)
    recommended_frequency = models.CharField(max_length=100)
    estimated_drone_time = models.CharField(max_length=50)
    trigger_response_time = models.CharField(max_length=50)
    probable_defects_max = models.TextField(blank=True, null=True)
    probable_defects_moderate = models.TextField(blank=True, null=True)
    inspection_type = models.ManyToManyField(InspectionType)

    def __str__(self):
        return self.risk_type

class DamageType(models.Model):
    name = models.CharField(max_length=150)  # e.g. "Hot Spots"
    drone_inspection = models.BooleanField(default=False)
    visual_inspection = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return self.email


class SolarPanels(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solar_panels')
    companyName = models.CharField(max_length=100)
    installationYear = models.CharField(max_length=100)
    image = models.ImageField(upload_to='solar_panels/', null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.companyName} - {self.user.email}"
    

class ManufacturerData(models.Model):
    name = models.CharField(max_length=250, blank=True, null=True)  # Company Name
    country = models.CharField(max_length=250, blank=True, null=True)  # Region
    series_name = models.CharField(max_length=250, blank=True, null=True)  # Series Name
    model_name = models.CharField(max_length=250, blank=True, null=True)  # Model Name

    panel_type = models.CharField(max_length=250, blank=True, null=True)
    cell_type = models.CharField(max_length=250, blank=True, null=True)
    cells_per_module = models.CharField(max_length=250, blank=True, null=True) # Converted from PositiveIntegerField
    
    power_range_wp = models.CharField(max_length=250, blank=True, null=True)
    pmax = models.CharField(max_length=250, blank=True, null=True)  # Converted from FloatField
    efficiency = models.CharField(max_length=250, blank=True, null=True)  # Converted from FloatField
    
    warranty_years = models.CharField(max_length=250, blank=True, null=True) # Converted from PositiveIntegerField
    primary_years = models.CharField(max_length=250, blank=True, null=True) # Converted from PositiveIntegerField
    output_power_percent = models.CharField(max_length=250, blank=True, null=True) # Converted from FloatField
    
    max_power_temp_coeff = models.CharField(max_length=250, blank=True, null=True) # Converted from FloatField
    voc_temp_coeff = models.CharField(max_length=250, blank=True, null=True) # Converted from FloatField
    isc_temp_coeff = models.CharField(max_length=250, blank=True, null=True) # Converted from FloatField

    front_glass = models.CharField(max_length=250, blank=True, null=True)
    frame_type = models.CharField(max_length=250, blank=True, null=True)
    junction_box = models.CharField(max_length=250, blank=True, null=True)
    cable_length_mm = models.CharField(max_length=250, blank=True, null=True) # Converted from PositiveIntegerField

    pdf_download_url = models.CharField(max_length=250, blank=True, null=True) # Converted from URLField
    product_url = models.CharField(max_length=250, blank=True, null=True) # Converted from URLField
    contact_url = models.CharField(max_length=250, blank=True, null=True) # Converted from URLField

    status = models.CharField(max_length=250, blank=True, null=True) # Default removed for consistency with nullability
    last_updated = models.CharField(max_length=250, blank=True, null=True) # Converted from DateTimeField

    def __str__(self):
        return f"{self.name} - {self.model_name}"

class Registrations(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    country = models.CharField(max_length=100)
    companyRole = models.CharField(max_length=150)
    areaOfInterest = models.CharField(max_length=150)
    company = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.email})"


class ContactForm(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    services = models.JSONField(default=list, blank=True)  # Stores array of services
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contact from {self.name} ({self.email})"

class Donation(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Under Review", "Under Review"),
        ("Scheduled for Pickup", "Scheduled for Pickup"),
        ("Collected", "Collected"),
        ("Rejected", "Rejected"),
    ]

    name = models.CharField(max_length=150)
    email = models.EmailField()
    dial_code = models.CharField(max_length=10, blank=True, null=True)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    panels = models.PositiveIntegerField()
    country = models.CharField(max_length=100)
    waste_image = models.ImageField(upload_to="donations/waste_images/", blank=True, null=True)
    site_image = models.ImageField(upload_to="donations/site_images/", blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Donation by {self.name} - {self.country} ({self.status})"
