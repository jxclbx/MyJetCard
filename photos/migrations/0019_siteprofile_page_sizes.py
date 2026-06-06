# Generated manually for per-viewer gallery page size preferences.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("photos", "0018_dataexportlog"),
    ]

    operations = [
        migrations.AddField(
            model_name="siteprofile",
            name="gallery_page_size",
            field=models.PositiveSmallIntegerField(default=24),
        ),
    ]
