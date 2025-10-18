from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import *

class UserResource(resources.ModelResource):
    class Meta:
        model = User

class SolarPanelsResource(resources.ModelResource):
    class Meta:
        model = SolarPanels

class InspectionTypeResource(resources.ModelResource):
    class Meta:
        model = InspectionType

class MaterialRecoveryResource(resources.ModelResource):
    class Meta:
        model = MaterialRecovery

class DamageTypeResource(resources.ModelResource):
    class Meta:
        model = DamageType

class ThermalRiskInspectionResource(resources.ModelResource):
    class Meta:
        model = ThermalRiskInspection

class DonationResource(resources.ModelResource):
    class Meta:
        model = Donation

class ManufacturerDataResource(resources.ModelResource):
    class Meta:
        model = ManufacturerData

class ContactFormDataResource(resources.ModelResource):
    class Meta:
        model = ContactForm

class RegistrationsDataResource(resources.ModelResource):
    class Meta:
        model = Registrations

@admin.register(User)
class UserAdmin(ImportExportModelAdmin):
    resource_class = UserResource
    list_display = ("email", "name", "is_active", "is_staff")

@admin.register(SolarPanels)
class SolarPanelsAdmin(ImportExportModelAdmin):
    resource_class = SolarPanelsResource
    list_display = ("companyName", "installationYear", "user", "created_at")

@admin.register(InspectionType)
class InspectionTypeAdmin(ImportExportModelAdmin):
    resource_class = InspectionTypeResource
    list_display = ("name",)

@admin.register(MaterialRecovery)
class MaterialRecoveryAdmin(ImportExportModelAdmin):
    resource_class = MaterialRecoveryResource
    list_display = ("material", "recovery_rate", "min_market_price", "max_market_price")

@admin.register(DamageType)
class DamageTypeAdmin(ImportExportModelAdmin):
    resource_class = DamageTypeResource
    list_display = ("name", "drone_inspection", "visual_inspection")

@admin.register(ThermalRiskInspection)
class ThermalRiskInspectionAdmin(ImportExportModelAdmin):
    resource_class = ThermalRiskInspectionResource
    list_display = ("risk_type", "recommended_frequency", "estimated_drone_time", "trigger_response_time")

@admin.register(Donation)
class DonationAdmin(ImportExportModelAdmin):
    resource_class = DonationResource
    list_display = ("name", "country", "panels", "status", "created_at")
    list_filter = ("status", "country")
    search_fields = ("name", "email", "phone")

@admin.register(ContactForm)
class ContactFormAdmin(ImportExportModelAdmin):
    resource_class = ContactFormDataResource
    list_display = ("name", "email", "message", "created_at")

@admin.register(Registrations)
class RegistrationsAdmin(ImportExportModelAdmin):
    resource_class = RegistrationsDataResource
    list_display = ("name", "email", "phone", "country", "company", "companyRole", "areaOfInterest", "created_at")

@admin.register(ManufacturerData)
class ManufacturerDataAdmin(ImportExportModelAdmin):
    resource_class = ManufacturerDataResource
    list_display = ("name", "model_name", "country", "warranty_years", "efficiency")
