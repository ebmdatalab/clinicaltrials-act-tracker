from django.urls import path

from frontend import views

urlpatterns = [
    path('', views.index),
    path('sponsor/<slug:slug>/', views.sponsor),
]
