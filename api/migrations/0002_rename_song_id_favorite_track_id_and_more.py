# Generated by Django 5.1.2 on 2024-10-29 11:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='favorite',
            old_name='song_id',
            new_name='track_id',
        ),
        migrations.RenameField(
            model_name='favorite',
            old_name='artist_name',
            new_name='track_name',
        ),
        migrations.RemoveField(
            model_name='favorite',
            name='album_image_url',
        ),
        migrations.RemoveField(
            model_name='favorite',
            name='song_name',
        ),
    ]
