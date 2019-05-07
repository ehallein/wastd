# Generated by Django 2.1.7 on 2019-05-07 04:22

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('occurrence', '0033_auto_20190506_1347'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnimalSex',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.SlugField(help_text='A unique, url-safe code.', max_length=500, unique=True, verbose_name='Code')),
                ('label', models.CharField(blank=True, help_text='A human-readable, self-explanatory label.', max_length=500, null=True, verbose_name='Label')),
                ('description', models.TextField(blank=True, help_text='A comprehensive description.', null=True, verbose_name='Description')),
            ],
            options={
                'ordering': ['code'],
                'abstract': False,
            },
        ),
        migrations.AlterModelOptions(
            name='animalobservation',
            options={'verbose_name': 'Animal Observation', 'verbose_name_plural': 'Animal Observations'},
        ),
        migrations.AlterModelOptions(
            name='habitatcomposition',
            options={'verbose_name': 'Habitat Composition', 'verbose_name_plural': 'Habitat Compositions'},
        ),
        migrations.AlterModelOptions(
            name='habitatcondition',
            options={'verbose_name': 'Habitat Condition', 'verbose_name_plural': 'Habitat Conditions'},
        ),
        migrations.AlterModelOptions(
            name='physicalsample',
            options={'verbose_name': 'Physical Sample', 'verbose_name_plural': 'Physical Samples'},
        ),
        migrations.AlterModelOptions(
            name='plantcount',
            options={'verbose_name': 'Plant Count', 'verbose_name_plural': 'Plant Counts'},
        ),
        migrations.AlterModelOptions(
            name='vegetationclassification',
            options={'verbose_name': 'Vegetation Classification', 'verbose_name_plural': 'Vegetation Classifications'},
        ),
        migrations.AlterField(
            model_name='areaencounter',
            name='source_id',
            field=models.CharField(default=uuid.UUID('b6e9dd1a-707f-11e9-a870-ecf4bb19b5fc'), help_text='The ID of the record in the original source, if available.', max_length=1000, verbose_name='Source ID'),
        ),
        migrations.AddField(
            model_name='animalobservation',
            name='sex',
            field=models.ForeignKey(blank=True, help_text='The sex of the primary observed animal.', null=True, on_delete=django.db.models.deletion.CASCADE, to='occurrence.AnimalSex', verbose_name='Animal Sex'),
        ),
    ]
