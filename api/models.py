from django.db import models
from django.contrib.auth.models import User

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    track_id = models.CharField(max_length=100, unique=True)  # Assuming each song has a unique ID
    track_name = models.CharField(max_length=255, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.track_id} - Favorited by {self.user.username}"
