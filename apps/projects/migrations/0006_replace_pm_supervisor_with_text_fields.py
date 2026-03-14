"""
Replace project_manager/supervisor User FKs with plain-text company + rep fields.
PM and Supervisor are external companies (NEC4 contract parties), not system users.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0005_remove_y2_y3_site_language_law_tribunal'),
    ]

    operations = [
        migrations.RemoveField(model_name='project', name='project_manager'),
        migrations.RemoveField(model_name='project', name='supervisor'),
        migrations.AddField(
            model_name='project',
            name='pm_company',
            field=models.CharField(
                max_length=255, blank=True,
                verbose_name='Project Manager Company',
                help_text='NEC4 Cl.14.2 — The company appointed as Project Manager.',
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='pm_representative',
            field=models.CharField(
                max_length=255, blank=True,
                verbose_name="PM's Named Representative",
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='pm_contact_email',
            field=models.EmailField(blank=True, verbose_name='PM Contact Email'),
        ),
        migrations.AddField(
            model_name='project',
            name='supervisor_company',
            field=models.CharField(
                max_length=255, blank=True,
                verbose_name='Supervisor Company',
                help_text='NEC4 Cl.14.4 — The company appointed as Supervisor.',
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='supervisor_representative',
            field=models.CharField(
                max_length=255, blank=True,
                verbose_name="Supervisor's Named Representative",
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='supervisor_contact_email',
            field=models.EmailField(blank=True, verbose_name='Supervisor Contact Email'),
        ),
    ]
