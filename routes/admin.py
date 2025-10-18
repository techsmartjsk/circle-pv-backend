from django.contrib import admin
from .models import *
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import ManufacturerData

admin.site.register(User)
admin.site.register(SolarPanels)
admin.site.register(InspectionType)
admin.site.register(MaterialRecovery)
admin.site.register(DamageType)
admin.site.register(ThermalRiskInspection)

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "panels", "status", "created_at")
    list_filter = ("status", "country")
    search_fields = ("name", "email", "phone")

class ManufacturerDataResource(resources.ModelResource):
    class Meta:
        model = ManufacturerData

class ContactFormDataResource(resources.ModelResource):
    class Meta:
        model = ContactForm

class RegistrationsDataResource(resources.ModelResource):
    class Meta:
        model = Registrations

@admin.register(ContactForm)
class ContactFormAdmin(ImportExportModelAdmin):
    resource_class = ContactFormDataResource
    list_display = ('name', 'email', 'message', 'created_at')

@admin.register(Registrations)
class RegistrationsAdmin(ImportExportModelAdmin):
    resource_class = RegistrationsDataResource
    list_display = ('name', 'email', 'phone', 'country', 'company', 'companyRole', 'areaOfInterest', 'created_at')

@admin.register(ManufacturerData)
class ManufacturerDataAdmin(ImportExportModelAdmin):
    resource_class = ManufacturerDataResource
    list_display = ('name', 'model_name', 'country', 'warranty_years', 'efficiency')