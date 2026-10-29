from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('users', '0003_auto_20250609_1724')]
    operations = [
        migrations.AddField(
            model_name='user', name='telegram_id',
            field=models.BigIntegerField(
                'Telegram ID', blank=True, null=True, unique=True,
                help_text='ID пользователя в Telegram для интеграции с ботом',
            ),
        ),
    ]
