from django.contrib.auth.decorators import login_required
from django.http  import JsonResponse
from drugs.models import UserPreset, Drug
import json

@login_required
def save_user_preset(request):
    """AJAX endpoint: Save a new user preset for notes fields"""
    data = json.loads(request.body)
    field = data.get('field_name')
    value = data.get('value')
    if field and value:
        UserPreset.objects.get_or_create(user=request.user,
                                         field_name=field,
                                         value=value)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Invalid data'}, status=400)

