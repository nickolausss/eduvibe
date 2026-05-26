from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('my/<str:session_key>/', views.my_scenarios, name='my-scenarios'),
    path('get-session-key/', views.get_session_key_api, name='get-session-key'),
    path('get-my-link/', views.get_my_link, name='get-my-link'),
]