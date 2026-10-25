from django.urls import path
from qrapp import destinations, views
from qrapp import batch_views

urlpatterns = [
    path("api/imports/<str:id>/status/", batch_views.status),
    path("api/imports/template/", batch_views.template),
    path("api/imports/inspect/", batch_views.inspect),
    path("api/imports/validate/", batch_views.validate),
    path("api/imports/<str:id>/step/", batch_views.step),
    path("api/imports/<str:id>/cancel/", batch_views.cancel),
    path("api/imports/<str:id>/download/", batch_views.download),
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
