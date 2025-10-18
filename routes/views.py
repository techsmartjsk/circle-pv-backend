import os
import numpy as np
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from skimage.io import imread
from skimage.transform import resize
from skimage.filters import sobel
import joblib
from .serializers import *
from .models import *
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import datetime
from django.db import transaction

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'ml_models', 'model_pipeline.pkl')
ENCODER_PATH = os.path.join(os.path.dirname(__file__), 'ml_models', 'label_encoder.pkl')

model = joblib.load(MODEL_PATH)
label_encoder = joblib.load(ENCODER_PATH)

TEMP_SURFACE_FLAT_TOLERANCE = 2         # minimal surface fluctuation
TEMP_AMBIENT_VARIATION = 5              # significant ambient swing
TEMP_OVERHEAT_MARGIN = 25               # excess heat above ambient
TEMP_UNDERHEAT_MARGIN = 10              # unusual cooling below ambient
TYPHOON_SPEED_THRESHOLD = 8             # typhoon threshold from flowchart "T8"

def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

def _safe_int(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default

def extract_image_features_from_array(img_resized):
    """
    Build a compact, robust feature vector for image-based classifier:
    - mean & std per channel
    - overall mean & std
    - dark / bright pixel fractions
    - edge mean & density
    """
    if img_resized is None:
        return np.zeros((1, 12), dtype=float)
    H, W, C = img_resized.shape
    flat = img_resized.reshape(-1, 3)
    means = flat.mean(axis=0)        
    stds = flat.std(axis=0)          
    overall_mean = flat.mean()       
    overall_std = flat.std()          
    lum = img_resized.mean(axis=2)   
    dark_frac = float((lum < 0.1).sum()) / lum.size
    bright_frac = float((lum > 0.9).sum()) / lum.size

    vec = np.concatenate([
        means.flatten(),
        stds.flatten(),
        np.array([overall_mean, overall_std, dark_frac, bright_frac])
    ])
    return vec.reshape(1, -1)  # shape (1, 12)

def compute_damage_type_from_temps(c1, c2, t1, t2):
    """
    Implements flowchart temperature branching and returns:
      (damage_type: str, notes: str)
    """
    if c1 is None or c2 is None:
        return "Unknown", "Missing surface temperature readings"

    # if ambient readings exist, check unresponsive sensors or abnormal behavior
    if t1 is not None and t2 is not None:
        # flat surface but ambient swings -> sensor/panel unresponsive
        if abs(c2 - c1) < TEMP_SURFACE_FLAT_TOLERANCE and abs(t2 - t1) > TEMP_AMBIENT_VARIATION:
            return "Sensor or panel unresponsive", "Surface flat while ambient swings"
    # overheating checks relative to ambient if ambient available
    if t2 is not None:
        if (c2 - t2) > TEMP_OVERHEAT_MARGIN:
            return "Critical overheating", f"C2-T2 > {TEMP_OVERHEAT_MARGIN}"
        if (c2 - t2) > 0 and (c2 - t2) <= TEMP_OVERHEAT_MARGIN:
            return "Excessive heating", "Moderate heating vs ambient"
    # underheat check: surface significantly lower than ambient min
    if t1 is not None:
        if (t1 - c1) > TEMP_UNDERHEAT_MARGIN:
            return "Unusual cooling", f"T1 - C1 > {TEMP_UNDERHEAT_MARGIN}"
    return "Normal", "Temperatures within expected ranges"

def compute_economic_S(system_cost, installed_capacity_kwp, annual_irradiation,
                       lifetime_years, electricity_rate, savings_per_year, maintenance_cost):
    """
    Rough implementation of flowchart economic S:
      - compute annual_energy = installed_capacity_kWp * annual_irradiation * (1 - loss_factor)
      - compute cost_per_kwh = system_cost / (annual_energy * lifetime_years)
      - compute S1 = (electricity_rate - cost_per_kwh) (theoretical saving per kWh)
      - normalize S1 by expected annual savings to get a dimensionless indicator S_theoretical
    Note: We do not attempt to implement PVGIS in-host; the caller should pass a loss_factor
    if available. We'll defensively handle zero / missing values.
    """
    try:
        if installed_capacity_kwp is None or annual_irradiation is None:
            return None, None

        # Loss factor placeholder: if caller provided a loss factor key, use it; else assume small loss
        # caller may pass 'lossFactor' in request.POST; we'll fetch it above in the main handler
    except Exception:
        return None, None

    # The main function will call this with proper values.
    return None, None  # placeholder - main function uses a small local implementation

@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def predict_damage(request):
    """
    Improved and defensive predict_damage implementing flowchart logic and covering edge cases.
    Returns a detailed JSON object describing:
      - model label & probability (if available)
      - computed S_value(s) and rationale
      - damage_type from temperature checks
      - recommended action (repair/replace/recycle/no-action) with rationale
      - action flags (send_inspection_request, send_reminders, schedule_drone_inspection)
    """
    if not request.FILES.get('image'):
        return JsonResponse({'error': 'POST an image'}, status=400)

    image_file = request.FILES['image']

    company_name = request.POST.get('companyName', 'Unknown')
    model_name = request.POST.get('modelName', None)
    installation_year = _safe_int(request.POST.get('installationYear'), datetime.datetime.now().year)
    savings_per_year = _safe_float(request.POST.get('savingsPerYear'), 0.0)
    maintenance_cost = _safe_float(request.POST.get('maintenanceCost'), 1.0)  # avoid /0
    kwh_generated = _safe_float(request.POST.get('kwhGenerated', 0.0), 0.0)

    promised_degradation = _safe_float(request.POST.get('promisedDegradationRate', 0.01), 0.01)
    current_degradation = _safe_float(request.POST.get('currentDegradationRate', 0.01), 0.01)
    current_typhoon_speed = _safe_float(request.POST.get('currentTyphoonSpeed', 0.0), 0.0)
    promised_wind_speed = _safe_float(request.POST.get('promisedWindBearingSpeed', 1.0), 1.0)
    warranty_age = _safe_int(request.POST.get('warrantyAge', 25), 25)
    x1 = _safe_int(request.POST.get('sensorAlert', 0), 0)
    x2 = _safe_int(request.POST.get('typhoonAlert', 0), 0)
    c1 = request.POST.get('C1')
    c2 = request.POST.get('C2')
    t1 = request.POST.get('T1')
    t2 = request.POST.get('T2') 

    c1 = None if c1 in (None, '', 'None') else _safe_float(c1, None)
    c2 = None if c2 in (None, '', 'None') else _safe_float(c2, None)
    t1 = None if t1 in (None, '', 'None') else _safe_float(t1, None)
    t2 = None if t2 in (None, '', 'None') else _safe_float(t2, None)

    installed_capacity_kwp = _safe_float(request.POST.get('installedCapacity_kWp', 0.0), 0.0)
    annual_irradiation = _safe_float(request.POST.get('annualIrradiation', 0.0), 0.0)  # kWh/m^2
    system_cost = _safe_float(request.POST.get('systemCost', 0.0), 0.0)
    electricity_rate = _safe_float(request.POST.get('electricityRate', 0.0), 0.0)
    loss_factor = _safe_float(request.POST.get('lossFactor', 0.10), 0.10)  # default 10% loss
    lifetime_years = _safe_int(request.POST.get('lifetimeYears', 25), 25)

    current_age = datetime.datetime.now().year - installation_year

    damage_type_temp, temp_notes = compute_damage_type_from_temps(c1, c2, t1, t2)

    if c1 is not None and c2 is not None and c2 < c1:
        damage_type_temp = "Sensor anomaly (C2 < C1)"
        temp_notes = "C2 < C1 (max < min) - possible sensor mis-reporting"

    if current_age < 0:
        current_age = 0  # defensive

    if current_age > 25 or current_age > warranty_age:
        try:
            solar_panel = SolarPanels.objects.create(
                user=request.user,
                companyName=company_name,
                installationYear=installation_year,
                image=image_file,
                latitude=request.POST.get('latitude'),
                longitude=request.POST.get('longitude'),
            )

            if hasattr(solar_panel, 'damage_type'):
                setattr(solar_panel, 'damage_type', 'End of life / recycle recommended')
            if hasattr(solar_panel, 'S_value'):
                setattr(solar_panel, 'S_value', 0.0)
            solar_panel.save()
        except Exception:
            pass

        return JsonResponse({
            'prediction': None,
            'damage_type': 'End of life / recycle recommended',
            'decision': 'Recycle Panel',
            'reason': 'Panel age exceeds lifetime or warranty',
            'saved_id': getattr(solar_panel, 'id', None)
        })

    S_sensor = None
    try:
        if x1 == 1:
            S_sensor = (savings_per_year / max(maintenance_cost, 1e-6)) * (
                promised_degradation / (current_degradation * current_age + 1)
            )
        elif x2 == 1:
            S_sensor = (savings_per_year / max(maintenance_cost, 1e-6)) * (
                (promised_degradation * promised_wind_speed) /
                (current_degradation * current_age * max(1.0, current_typhoon_speed) + 1)
            )
        else:
            S_sensor = (savings_per_year / max(maintenance_cost, 1e-6)) * (
                promised_degradation / (current_degradation + current_age + 1)
            )
    except Exception:
        S_sensor = None

    S_theoretical = None
    try:
        if installed_capacity_kwp > 0 and annual_irradiation > 0 and lifetime_years > 0 and system_cost > 0:
            annual_energy = installed_capacity_kwp * annual_irradiation * max(0.0, (1.0 - loss_factor))
            if annual_energy > 0:
                cost_per_kwh = system_cost / (annual_energy * lifetime_years)
                S1 = (electricity_rate - cost_per_kwh)
                denom = max(1e-6, savings_per_year)
                S_theoretical = S1 / (denom / (annual_energy + 1e-6))  # normalized indicator
    except Exception:
        S_theoretical = None

    S_candidates = [v for v in (S_sensor, S_theoretical) if v is not None]
    S_value = S_candidates[0] if S_candidates else 0.0

    try:
        S_value_float = float(S_value)
    except Exception:
        S_value_float = 0.0

    try:
        img = imread(image_file)
        if img.ndim == 2:
            img = np.stack((img,) * 3, axis=-1)
        elif img.shape[2] == 4:
            img = img[..., :3]
        img_resized = resize(img, (128, 128), anti_aliasing=True)
        grey = img_resized.mean(axis=-1)
        edges = sobel(grey)
        edge_mean = float(edges.mean())
        edge_density = float((edges > edges.mean()).sum()) / edges.size
        image_feat = extract_image_features_from_array(img_resized)  # shape (1, n)
        image_feat = np.concatenate([image_feat, np.array([[edge_mean, edge_density]])], axis=1)
    except Exception as e:
        # fallback if image read fails
        image_feat = np.zeros((1, 14), dtype=float)
        edge_mean = 0.0
        edge_density = 0.0

    label = "Unknown"
    damage_prob = None
    try:
        pred = model.predict(image_feat)
        if hasattr(label_encoder, 'inverse_transform'):
            try:
                label = label_encoder.inverse_transform([pred[0]])[0]
            except Exception:
                label = str(pred[0])
        else:
            label = str(pred[0])
        if hasattr(model, 'predict_proba'):
            try:
                probs = model.predict_proba(image_feat)[0]
                if hasattr(model, 'classes_'):
                    idx = list(model.classes_).index(pred[0])
                    damage_prob = float(probs[idx])
                else:
                    damage_prob = float(max(probs))
            except Exception:
                damage_prob = None
    except Exception:
        label = "Prediction failed"
        damage_prob = None

    damage_score = None
    if damage_prob is not None:
        if label and label.lower() in ('normal', 'no_damage', 'ok'):
            damage_score = 1.0 - damage_prob  # lower damage
        else:
            damage_score = damage_prob       # higher prob => more damaged
    else:
        damage_score = float(min(1.0, max(0.0, edge_density * 2.0 * (1.0 if S_value_float < 1.0 else 0.5))))

    decision = "Undetermined"
    action_recommendations = []
    warranty_active = (current_age <= warranty_age)
    severe_threshold = 0.6
    medium_threshold = 0.3

    if S_value_float >= 1.0 and damage_score < medium_threshold and damage_type_temp == "Normal":
        decision = "Panel in good condition"
        action_recommendations.append("No immediate action required")
    else:
        if damage_type_temp in ("Critical overheating", "Sensor or panel unresponsive"):
            if warranty_active:
                decision = "Replace with warranty"
                action_recommendations.append("Issue replacement under warranty; schedule inspection")
            else:
                decision = "Replace without warranty"
                action_recommendations.append("Recommend replacement; warranty expired")
            action_recommendations.append("Schedule urgent inspection (drone or technician)")
        else:
            if damage_score >= severe_threshold:
                if warranty_active:
                    decision = "Replace with warranty"
                    action_recommendations.append("High damage detected; replace under warranty")
                else:
                    decision = "Replace without warranty"
                    action_recommendations.append("High damage detected; recommend replacement")
            elif medium_threshold <= damage_score < severe_threshold:
                if warranty_active:
                    decision = "Repair with warranty"
                    action_recommendations.append("Moderate damage; repair covered under warranty")
                else:
                    decision = "Repair without warranty"
                    action_recommendations.append("Moderate damage; repair recommended (out-of-warranty)")
            else:
                decision = "Panel in good condition"
                action_recommendations.append("Minor / uncertain damage; monitor or request user confirmation")

    send_reminders = False
    schedule_drone_inspection = False
    send_inspection_request = False
    if x2 == 1 or current_typhoon_speed >= TYPHOON_SPEED_THRESHOLD:
        send_inspection_request = True
        schedule_drone_inspection = True
        send_reminders = True
        action_recommendations.append("Typhoon alert: schedule drone inspection within 48 hours after typhoon")
    if x1 == 1 and damage_type_temp.startswith("Sensor"):
        send_reminders = True
        action_recommendations.append("Sensor abnormal: request sensor diagnostics and visual inspection")

    saved_id = None
    try:
        with transaction.atomic():
            solar_panel = SolarPanels.objects.create(
                user=request.user,
                companyName=company_name,
                installationYear=installation_year,
                image=image_file,
                latitude=request.POST.get('latitude'),
                longitude=request.POST.get('longitude')
            )
            optional_updates = {
                'damage_type': damage_type_temp,
                'damage_label': label,
                'damage_probability': damage_prob,
                'S_value': S_value_float,
                'decision': decision,
                'damage_score': damage_score,
                'edge_mean': edge_mean,
                'edge_density': edge_density,
            }
            for k, v in optional_updates.items():
                if hasattr(solar_panel, k):
                    try:
                        setattr(solar_panel, k, v)
                    except Exception:
                        pass
            solar_panel.save()
            saved_id = solar_panel.id
    except Exception:
        saved_id = None

    response_payload = {
        'prediction_label': label,
        'damage_probability': damage_prob,
        'damage_score': damage_score,
        'damage_type_from_temps': damage_type_temp,
        'temperature_notes': temp_notes,
        'S_value': S_value_float,
        'S_components': {
            'sensor_based_S': S_sensor,
            'theoretical_S': S_theoretical
        },
        'decision': decision,
        'action_recommendations': action_recommendations,
        'send_inspection_request': send_inspection_request,
        'schedule_drone_inspection': schedule_drone_inspection,
        'send_reminders': send_reminders,
        'saved_id': saved_id,
    }

    return JsonResponse(response_payload)

class TokenVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        response_data = {
            'status': 'success',
            'user_id': user.id,
            'email': user.email,
        }
        return Response(response_data)
    
@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data

            refresh = RefreshToken.for_user(user)

            return Response({
                "message": "Login successful",
                "user": user.email,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class RegistrationCreateView(generics.CreateAPIView):
    queryset = Registrations.objects.all()
    serializer_class = RegistrationSerializer


class RegistrationListView(generics.ListAPIView):
    queryset = Registrations.objects.all().order_by('-created_at')
    serializer_class = RegistrationSerializer


@method_decorator(csrf_exempt, name='dispatch')
class ContactFormCreateView(generics.CreateAPIView):
    queryset = ContactForm.objects.all()
    serializer_class = ContactFormSerializer


class ContactFormListView(generics.ListAPIView):
    queryset = ContactForm.objects.all().order_by('-created_at')
    serializer_class = ContactFormSerializer

class ManufacturerDataListView(generics.ListAPIView):
    queryset = ManufacturerData.objects.all()
    serializer_class = ManufacturerDataSerializer