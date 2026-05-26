from django.urls import path
from . import views

urlpatterns = [
    path('', views.scenario_list, name='scenario-list'),
    path('create/', views.scenario_create, name='scenario-create'),
    path('<int:pk>/', views.scenario_detail, name='scenario-detail'),
    path('<int:pk>/edit/', views.scenario_edit, name='scenario-edit'),
    path('<int:pk>/delete/', views.scenario_delete, name='scenario-delete'),
    path('<int:pk>/generate/', views.scenario_generate, name='scenario-generate'),
    path('<int:pk>/generate/auto/', views.scenario_generate_auto, name='scenario-generate-auto'),
    path('<int:pk>/generate/api/', views.scenario_generate_api, name='scenario-generate-api'),
    path('<int:pk>/regenerate-block/<int:block_index>/', views.scenario_regenerate_block_api, name='scenario-regenerate-block'),
    path('<int:pk>/export/pdf/', views.scenario_export_pdf, name='scenario-export-pdf'),
    path('<int:pk>/export/docx/', views.scenario_export_docx, name='scenario-export-docx'),
    path('<int:pk>/share/', views.scenario_share, name='scenario-share'),
    path('<int:pk>/unshare/', views.scenario_unshare, name='scenario-unshare'),
    path('<int:pk>/set-date/', views.scenario_set_date, name='scenario-set-date'),
    path('<int:pk>/remove-date/', views.scenario_remove_date, name='scenario-remove-date'),
    path('<int:pk>/qrcode/', views.scenario_qrcode, name='scenario-qrcode'),
    path('calendar/upload-plan/', views.calendar_upload_plan, name='calendar-upload-plan'),
    path('calendar/delete-theme/', views.calendar_delete_theme, name='calendar-delete-theme'),
    path('<int:pk>/versions/', views.scenario_versions, name='scenario-versions'),
    path('<int:pk>/versions/<int:version_number>/', views.scenario_version_detail, name='scenario-version-detail'),
    path('<int:pk>/versions/<int:version_number>/restore/', views.scenario_restore_version, name='scenario-restore-version'),
    path('<int:pk>/versions/<int:version_number>/delete/', views.scenario_delete_version, name='scenario-delete-version'),
    path('<int:pk>/versions/compare/', views.scenario_compare_versions, name='scenario-compare-versions'),
    path('statistics/', views.scenario_statistics, name='scenario-statistics'),
    
]