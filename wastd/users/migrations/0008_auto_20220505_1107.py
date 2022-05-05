# Generated by Django 3.2.13 on 2022-05-05 03:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_auto_20210505_1101'),
    ]

    operations = [
        migrations.CreateModel(
            name='Organisation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.SlugField(help_text='A unique, url-safe code.', max_length=500, unique=True, verbose_name='Code')),
                ('label', models.CharField(blank=True, help_text='A human-readable, self-explanatory label.', max_length=500, null=True, verbose_name='Label')),
                ('description', models.TextField(blank=True, help_text='A comprehensive description.', null=True, verbose_name='Description')),
            ],
            options={
                'ordering': ['code'],
            },
        ),
        migrations.AlterField(
            model_name='user',
            name='affiliation',
            field=models.TextField(blank=True, help_text='The organisational affiliation of the user as free text.', verbose_name='Affiliation'),
        ),
        migrations.AddField(
            model_name='user',
            name='organisations',
            field=models.ManyToManyField(blank=True, help_text='The organisational affiliation is used to control data visibility and access. A user can be a member of several Organisations.', related_name='members', to='users.Organisation'),
        ),
    ]
