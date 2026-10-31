from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_loginpagelabel"),
    ]

    operations = [
        migrations.AddField(
            model_name="loginpagelabel",
            name="page_title",
            field=models.CharField(default="", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="loginpagelabel",
            name="page_description",
            field=models.CharField(default="", max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="loginpagelabel",
            name="language_switcher_label",
            field=models.CharField(default="", max_length=50),
            preserve_default=False,
        ),
    ]
