from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('dj_rest_auth.urls')),  # Login, Logout, Password Reset, etc.
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),  # Registration
    path('api/', include('api.urls')),  # Your app's endpoints
]
