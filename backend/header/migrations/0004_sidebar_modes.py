import django.core.validators
from django.db import migrations, models

import base.fields


def label(text, max_length=50):
    # The rows get their real texts in every language from load_sample or the admin.
    return models.CharField(default=text, max_length=max_length)


class Migration(migrations.Migration):

    dependencies = [
        ("header", "0003_sidebar_categories"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="sidebaritem", name="unique_sidebar_item_lang_url"),
        migrations.AlterModelOptions(
            name="sidebaritem",
            options={"ordering": ["mode", "order", "id"], "verbose_name_plural": "Sidebar items"},
        ),
        migrations.AddField(
            model_name="sidebaritem",
            name="mode",
            field=models.CharField(
                choices=[("sports", "Sports"), ("casino", "Casino")], db_index=True, default="casino", max_length=10
            ),
        ),
        migrations.AddField(
            model_name="sidebaritem",
            name="group",
            field=models.CharField(
                blank=True, choices=[("", "None"), ("leagues", "Leagues"), ("my", "My Lumora")], max_length=10
            ),
        ),
        migrations.AddField(
            model_name="sidebaritem",
            name="icon",
            field=models.FileField(
                blank=True,
                max_length=255,
                upload_to="images/sidebar/",
                validators=[
                    django.core.validators.FileExtensionValidator(["jpg", "jpeg", "png", "webp", "gif"]),
                    base.fields.validate_image_size,
                    base.fields.validate_image_content,
                ],
            ),
        ),
        migrations.AlterField(
            model_name="sidebaritem",
            name="category",
            field=models.CharField(
                blank=True,
                choices=[("slot", "Slot"), ("crash", "Crash"), ("table", "Table"), ("instant", "Instant"), ("sports", "Sports")],
                help_text="Casino only. Set: the item filters the lobby, its url must be /casino?category=<code>",
                max_length=16,
            ),
        ),
        migrations.AddConstraint(
            model_name="sidebaritem",
            constraint=models.UniqueConstraint(fields=("lang", "mode", "url"), name="unique_sidebar_item_lang_mode_url"),
        ),
        migrations.AddField(model_name="headerlabel", name="sports_mode", field=label("Sports", 30), preserve_default=False),
        migrations.AddField(model_name="headerlabel", name="casino_mode", field=label("Casino", 30), preserve_default=False),
        migrations.AddField(
            model_name="headerlabel", name="mode_switch_label", field=label("Section"), preserve_default=False
        ),
        migrations.AddField(model_name="headerlabel", name="leagues_group", field=label("Leagues"), preserve_default=False),
        migrations.AddField(
            model_name="headerlabel", name="my_lumora_group", field=label("My Lumora"), preserve_default=False
        ),
    ]
