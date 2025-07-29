from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import DicomServerConfig, FacilityAETitle, DicomTransferLog
from viewer.models import Facility
import json


class DicomServerConfigView(LoginRequiredMixin, DetailView):
    """View for DICOM server configuration"""
    model = DicomServerConfig
    template_name = 'dicom_server/config.html'
    context_object_name = 'config'
    
    def get_object(self):
        # Get or create the default configuration
        config, created = DicomServerConfig.objects.get_or_create(
            is_active=True,
            defaults={
                'name': 'Noctis DICOM Server',
                'ae_title': 'NOCTIS',
                'port': 11112,
                'max_pdu_length': 65536
            }
        )
        return config
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['facility_ae_titles'] = FacilityAETitle.objects.filter(is_active=True)
        context['recent_transfers'] = DicomTransferLog.objects.all()[:50]
        context['is_admin'] = self.request.user.is_superuser
        return context


@login_required
@require_http_methods(['POST'])
def update_server_config(request):
    """Update DICOM server configuration"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        config = DicomServerConfig.objects.filter(is_active=True).first()
        
        if not config:
            config = DicomServerConfig.objects.create(
                name=data.get('name', 'Noctis DICOM Server'),
                ae_title=data.get('ae_title', 'NOCTIS'),
                port=data.get('port', 11112),
                max_pdu_length=data.get('max_pdu_length', 65536)
            )
        else:
            config.name = data.get('name', config.name)
            config.ae_title = data.get('ae_title', config.ae_title)
            config.port = data.get('port', config.port)
            config.max_pdu_length = data.get('max_pdu_length', config.max_pdu_length)
            config.save()
        
        return JsonResponse({
            'success': True,
            'config': {
                'id': config.id,
                'name': config.name,
                'ae_title': config.ae_title,
                'port': config.port,
                'max_pdu_length': config.max_pdu_length
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(['POST'])
def generate_facility_ae_title(request, facility_id):
    """Generate AE title for a facility"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        facility = get_object_or_404(Facility, id=facility_id)
        ae_title = FacilityAETitle.generate_ae_title(facility)
        
        return JsonResponse({
            'success': True,
            'ae_title': {
                'id': ae_title.id,
                'facility_name': facility.name,
                'ae_title': ae_title.ae_title,
                'port': ae_title.port
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(['DELETE'])
def delete_facility_ae_title(request, ae_title_id):
    """Delete a facility AE title"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        ae_title = get_object_or_404(FacilityAETitle, id=ae_title_id)
        ae_title.is_active = False
        ae_title.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def get_transfer_logs(request):
    """Get DICOM transfer logs"""
    logs = DicomTransferLog.objects.all()[:100]
    
    return JsonResponse({
        'logs': [{
            'id': log.id,
            'transfer_type': log.transfer_type,
            'calling_ae_title': log.calling_ae_title,
            'called_ae_title': log.called_ae_title,
            'patient_name': log.patient_name,
            'patient_id': log.patient_id,
            'status': log.status,
            'bytes_transferred': log.bytes_transferred,
            'transfer_time': log.transfer_time,
            'created_at': log.created_at.isoformat()
        } for log in logs]
    })


@login_required
def server_status(request):
    """Get DICOM server status"""
    config = DicomServerConfig.objects.filter(is_active=True).first()
    active_ae_titles = FacilityAETitle.objects.filter(is_active=True)
    
    return JsonResponse({
        'server_active': config is not None,
        'config': {
            'name': config.name if config else 'Noctis DICOM Server',
            'ae_title': config.ae_title if config else 'NOCTIS',
            'port': config.port if config else 11112,
            'max_pdu_length': config.max_pdu_length if config else 65536
        },
        'facility_ae_titles': [{
            'id': ae.id,
            'facility_name': ae.facility.name,
            'ae_title': ae.ae_title,
            'port': ae.port
        } for ae in active_ae_titles],
        'total_transfers': DicomTransferLog.objects.count(),
        'recent_transfers': DicomTransferLog.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(hours=24)
        ).count()
    })