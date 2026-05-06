import uuid

import pytest

from django.db import connection, models
from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone

from apps.core.models import SoftDeleteModel, TimestampedModel


class ConcreteItem(SoftDeleteModel, TimestampedModel):
    name = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        app_label = "core"


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        with connection.schema_editor() as schema_editor:
            try:
                schema_editor.create_model(ConcreteItem)
            except (ProgrammingError, OperationalError):
                pass
        yield
        with connection.schema_editor() as schema_editor:
            try:
                schema_editor.delete_model(ConcreteItem)
            except (ProgrammingError, OperationalError):
                pass


@pytest.mark.django_db
def test_soft_delete_sets_deleted_at():
    item = ConcreteItem.all_objects.create()
    assert item.deleted_at is None
    item.delete()
    assert item.deleted_at is not None


@pytest.mark.django_db
def test_objects_manager_excludes_deleted():
    item = ConcreteItem.all_objects.create()
    item.delete()
    assert ConcreteItem.objects.filter(pk=item.pk).count() == 0


@pytest.mark.django_db
def test_all_objects_includes_deleted():
    item = ConcreteItem.all_objects.create()
    item.delete()
    assert ConcreteItem.all_objects.filter(pk=item.pk).count() == 1


@pytest.mark.django_db
def test_soft_delete_queryset_alive():
    unique = str(uuid.uuid4())[:8]
    alive_item = ConcreteItem.objects.create(name=f"alive-{unique}")
    dead_item = ConcreteItem.all_objects.create(name=f"dead-{unique}")
    dead_item.delete()
    qs_alive = ConcreteItem.all_objects.alive().filter(
        name__startswith=f"alive-{unique}"
    )
    assert alive_item in qs_alive
    assert dead_item not in qs_alive


@pytest.mark.django_db
def test_soft_delete_queryset_dead():
    unique = str(uuid.uuid4())[:8]
    alive_item = ConcreteItem.objects.create(name=f"alive-{unique}")
    dead_item = ConcreteItem.all_objects.create(name=f"dead-{unique}")
    dead_item.delete()
    qs_dead = ConcreteItem.all_objects.dead().filter(name__startswith=f"dead-{unique}")
    assert dead_item in qs_dead
    assert alive_item not in qs_dead


@pytest.mark.django_db
def test_soft_delete_queryset_bulk():
    """QuerySet.soft_delete() sets deleted_at on all matching records."""
    item1 = ConcreteItem.objects.create(name="item1")
    item2 = ConcreteItem.objects.create(name="item2")
    ConcreteItem.all_objects.filter(name__startswith="item").soft_delete()
    item1.refresh_from_db()
    item2.refresh_from_db()
    assert item1.deleted_at is not None
    assert item2.deleted_at is not None


@pytest.mark.django_db
def test_hard_delete_removes_from_db():
    item = ConcreteItem.all_objects.create()
    pk = item.pk
    item.hard_delete()
    assert ConcreteItem.all_objects.filter(pk=pk).count() == 0


@pytest.mark.django_db
def test_timestamped_model_sets_created_at():
    before = timezone.now()
    item = ConcreteItem.all_objects.create()
    after = timezone.now()
    assert item.created_at is not None
    assert before <= item.created_at <= after
