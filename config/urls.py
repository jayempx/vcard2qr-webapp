from django.urls import path
from qrapp import destinations, views

urlpatterns = [
    path("", views.app),
    path("health/", views.health),
    path("api/unlock/", views.unlock),
    path("api/lock/", views.lock),
    path("api/records/", views.records),
    path("api/records/<str:id>/", views.record),
    path("api/preview/", views.export),
    path("api/export/", views.export),
    path("q/<str:id>/", destinations.destination),
    path("q/<str:id>/contact.vcf", destinations.destination, {"download": "contact.vcf"}),
    path("q/<str:id>/event.ics", destinations.destination, {"download": "event.ics"}),
]
