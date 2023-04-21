# Generated by Django 1.10.8 on 2017-10-03 21:29

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("forum", "0014_topic_github_issue"),
    ]

    operations = [
        migrations.AlterField(
            model_name="category",
            name="position",
            field=models.IntegerField(default=0, verbose_name="Position"),
        ),
        migrations.AlterField(
            model_name="category",
            name="slug",
            field=models.SlugField(
                help_text="Ces slugs vont provoquer des conflits d'URL et sont donc interdits : notifications resolution_alerte sujet sujets message messages",
                max_length=80,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="category",
            name="title",
            field=models.CharField(max_length=80, verbose_name="Titre"),
        ),
        migrations.AlterField(
            model_name="forum",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="forum.Category", verbose_name="Catégorie"
            ),
        ),
        migrations.AlterField(
            model_name="forum",
            name="position_in_category",
            field=models.IntegerField(blank=True, db_index=True, null=True, verbose_name="Position dans la catégorie"),
        ),
        migrations.AlterField(
            model_name="forum",
            name="subtitle",
            field=models.CharField(max_length=200, verbose_name="Sous-titre"),
        ),
        migrations.AlterField(
            model_name="forum",
            name="title",
            field=models.CharField(max_length=80, verbose_name="Titre"),
        ),
        migrations.AlterField(
            model_name="post",
            name="search_engine_already_indexed",
            field=models.BooleanField(db_index=True, default=False, verbose_name="Déjà indexé par ES"),
        ),
        migrations.AlterField(
            model_name="post",
            name="search_engine_flagged",
            field=models.BooleanField(db_index=True, default=True, verbose_name="Doit être (ré)indexé par ES"),
        ),
        migrations.AlterField(
            model_name="post",
            name="is_useful",
            field=models.BooleanField(default=False, verbose_name="Est utile"),
        ),
        migrations.AlterField(
            model_name="post",
            name="topic",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="forum.Topic", verbose_name="Sujet"
            ),
        ),
        migrations.AlterField(
            model_name="topic",
            name="author",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="topics",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Auteur",
            ),
        ),
        migrations.AlterField(
            model_name="topic",
            name="search_engine_already_indexed",
            field=models.BooleanField(db_index=True, default=False, verbose_name="Déjà indexé par ES"),
        ),
        migrations.AlterField(
            model_name="topic",
            name="search_engine_flagged",
            field=models.BooleanField(db_index=True, default=True, verbose_name="Doit être (ré)indexé par ES"),
        ),
        migrations.AlterField(
            model_name="topic",
            name="forum",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="forum.Forum", verbose_name="Forum"
            ),
        ),
        migrations.AlterField(
            model_name="topic",
            name="is_locked",
            field=models.BooleanField(db_index=True, default=False, verbose_name="Est verrouillé"),
        ),
        migrations.AlterField(
            model_name="topic",
            name="is_solved",
            field=models.BooleanField(db_index=True, default=False, verbose_name="Est résolu"),
        ),
        migrations.AlterField(
            model_name="topic",
            name="is_sticky",
            field=models.BooleanField(db_index=True, default=False, verbose_name="Est en post-it"),
        ),
        migrations.AlterField(
            model_name="topic",
            name="last_message",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="last_message",
                to="forum.Post",
                verbose_name="Dernier message",
            ),
        ),
        migrations.AlterField(
            model_name="topic",
            name="pubdate",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Date de création"),
        ),
        migrations.AlterField(
            model_name="topic",
            name="subtitle",
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name="Sous-titre"),
        ),
        migrations.AlterField(
            model_name="topic",
            name="tags",
            field=models.ManyToManyField(blank=True, db_index=True, to="utils.Tag", verbose_name="Tags du forum"),
        ),
        migrations.AlterField(
            model_name="topic",
            name="title",
            field=models.CharField(max_length=160, verbose_name="Titre"),
        ),
        migrations.AlterField(
            model_name="topic",
            name="update_index_date",
            field=models.DateTimeField(
                auto_now=True,
                db_index=True,
                verbose_name="Date de dernière modification pour la réindexation partielle",
            ),
        ),
    ]
