# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('storlet', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Dependency',
            fields=[
                ('name', models.CharField(max_length=100, serialize=False, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ('created_at',),
            },
        ),
        migrations.AddField(
            model_name='storlet',
            name='interface_version',
            field=models.CharField(default=1.0, max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='storlet',
            name='lenguage',
            field=models.CharField(default='java', max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='storlet',
            name='main_class',
            field=models.CharField(default='org.package.mainclass', max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='storlet',
            name='object_metadata',
            field=models.CharField(default='no', max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='storlet',
            name='dependency',
            field=models.ManyToManyField(to='storlet.Dependency'),
        ),
    ]
