from django.urls import path

from . import views

urlpatterns = [
    path('', views.ListTextGenerator.as_view(), name='index'),
    path('<int:pk>/', views.DetailTextGenerator.as_view(), name='detail'),
    path('generate/', views.generate, name='generate'),
]
