from django.conf.urls import url, include

urlpatterns = [
    url(r'', include('authentication.urls', namespace='authentication')),
    url(r'^visage/', include('visage.urls', namespace='visage')),
]
