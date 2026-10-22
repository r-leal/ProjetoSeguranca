import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tarefa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150)),
                ('descricao', models.TextField(blank=True)),
                ('data_prazo', models.DateField(blank=True, null=True)),
                ('estado', models.CharField(choices=[('esperando', 'Esperando'), ('em_andamento', 'Em andamento'), ('concluido', 'Concluído')], default='esperando', max_length=20)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tarefas', to='usuarios.usuario')),
            ],
        ),
    ]
