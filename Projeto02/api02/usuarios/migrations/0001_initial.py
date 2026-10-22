from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Usuario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
                ('sobrenome', models.CharField(max_length=100)),
                ('data_nascimento', models.DateField(blank=True, null=True)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('senha', models.CharField(max_length=32)),
                ('papel', models.CharField(choices=[('usuario', 'Usuário'), ('admin', 'Admin'), ('gerente', 'Gerente')], default='usuario', max_length=20)),
            ],
        ),
    ]
