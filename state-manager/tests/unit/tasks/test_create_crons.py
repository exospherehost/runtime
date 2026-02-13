"""
Tests for create_crons function to improve code coverage.
These are pure unit tests that mock DatabaseTriggers to avoid database dependency.
Environment variables are provided by CI (see .github/workflows/test-state-manager.yml).
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

# Environment variables are set by CI workflow
# For local testing, these should be set before running tests
# See: .github/workflows/test-state-manager.yml

from app.tasks.verify_graph import create_crons
from app.models.trigger_models import Trigger, TriggerTypeEnum

# Helper function to create trigger value dict
def make_trigger_value(expression: str, timezone: str = None):
    """Helper to create trigger value dict with required 'type' field"""
    result = {"type": TriggerTypeEnum.CRON, "expression": expression}
    if timezone is not None:
        result["timezone"] = timezone
    return result


@pytest.mark.asyncio
async def test_create_crons_with_america_new_york_timezone():
    """Test create_crons processes America/New_York timezone correctly"""
    graph_template = MagicMock()
    graph_template.name = "test_graph"
    graph_template.namespace = "test_ns"
    graph_template.triggers = [
        Trigger(
            value=make_trigger_value("0 9 * * *", "America/New_York")
        )
    ]

    # Mock DatabaseTriggers class and insert_many method
    with patch('app.tasks.verify_graph.DatabaseTriggers') as mock_db_class:
        # Mock instances that will be created
        mock_instance = MagicMock()
        mock_db_class.return_value = mock_instance
        mock_db_class.insert_many = AsyncMock()

        await create_crons(graph_template)

        # Verify DatabaseTriggers was instantiated with correct parameters
        assert mock_db_class.called
        call_kwargs = mock_db_class.call_args[1]
        assert call_kwargs['timezone'] == "America/New_York"
        assert call_kwargs['expression'] == "0 9 * * *"
        assert call_kwargs['graph_name'] == "test_graph"
        assert call_kwargs['namespace'] == "test_ns"

        # Verify insert_many was called with the list of triggers
        assert mock_db_class.insert_many.called


@pytest.mark.asyncio
async def test_create_crons_with_default_utc_timezone():
    """Test create_crons uses UTC as default when timezone not specified"""
    graph_template = MagicMock()
    graph_template.name = "test_graph"
    graph_template.namespace = "test_ns"
    graph_template.triggers = [
        Trigger(
            value=make_trigger_value("0 9 * * *")  # No timezone specified
        )
    ]

    with patch('app.tasks.verify_graph.DatabaseTriggers') as mock_db_class:
        mock_db_class.return_value = MagicMock()
        mock_db_class.insert_many = AsyncMock()

        await create_crons(graph_template)

        # Verify default UTC timezone was used
        call_kwargs = mock_db_class.call_args[1]
        assert call_kwargs['timezone'] == "UTC"
        assert mock_db_class.insert_many.called


@pytest.mark.asyncio
async def test_create_crons_with_europe_london_timezone():
    """Test create_crons handles Europe/London timezone"""
    graph_template = MagicMock()
    graph_template.name = "test_graph"
    graph_template.namespace = "test_ns"
    graph_template.triggers = [
        Trigger(
            value=make_trigger_value("0 17 * * *", "Europe/London")
        )
    ]

    with patch('app.tasks.verify_graph.DatabaseTriggers') as mock_db_class:
        mock_db_class.return_value = MagicMock()
        mock_db_class.insert_many = AsyncMock()

        await create_crons(graph_template)

        call_kwargs = mock_db_class.call_args[1]
        assert call_kwargs['timezone'] == "Europe/London"
        assert call_kwargs['expression'] == "0 17 * * *"
        assert mock_db_class.insert_many.called


@pytest.mark.asyncio
async def test_create_crons_with_multiple_different_timezones():
    """Test create_crons handles multiple triggers with different timezones"""
    graph_template = MagicMock()
    graph_template.name = "test_graph"
    graph_template.namespace = "test_ns"
    graph_template.triggers = [
        Trigger(
            value=make_trigger_value("0 9 * * *", "America/New_York")
        ),
        Trigger(
            value=make_trigger_value("0 17 * * *", "Europe/London")
        )
    ]

    with patch('app.tasks.verify_graph.DatabaseTriggers') as mock_db_class:
        mock_db_class.return_value = MagicMock()
        mock_db_class.insert_many = AsyncMock()

        await create_crons(graph_template)

        # Should be called twice (one for each trigger)
        assert mock_db_class.call_count == 2

        # Verify insert_many was called once with list of 2 triggers
        assert mock_db_class.insert_many.call_count == 1
        insert_call_args = mock_db_class.insert_many.call_args[0][0]
        assert len(insert_call_args) == 2


@pytest.mark.asyncio
async def test_create_crons_skips_insert_when_no_triggers():
    """Test create_crons doesn't call insert_many when no CRON triggers exist"""
    graph_template = MagicMock()
    graph_template.name = "test_graph"
    graph_template.namespace = "test_ns"
    graph_template.triggers = []

    with patch('app.tasks.verify_graph.DatabaseTriggers') as mock_db_class:
        mock_db_class.insert_many = AsyncMock()

        await create_crons(graph_template)

        # Verify insert_many was NOT called (no triggers to insert)
        assert not mock_db_class.insert_many.called
        # DatabaseTriggers should not have been instantiated
        assert mock_db_class.call_count == 0


@pytest.mark.asyncio
async def test_create_crons_deduplicates_same_expression_and_timezone():
    """Test create_crons deduplicates triggers with same expression and timezone"""
    graph_template = MagicMock()
    graph_template.name = "test_graph"
    graph_template.namespace = "test_ns"
    graph_template.triggers = [
        Trigger(
            value=make_trigger_value("0 9 * * *", "America/New_York")
        ),
        Trigger(
            value=make_trigger_value("0 9 * * *", "America/New_York")
        )
    ]

    with patch('app.tasks.verify_graph.DatabaseTriggers') as mock_db_class:
        mock_db_class.return_value = MagicMock()
        mock_db_class.insert_many = AsyncMock()

        await create_crons(graph_template)

        # Should only create one DatabaseTriggers instance (deduplicated)
        assert mock_db_class.call_count == 1

        # insert_many should be called with list of 1
        insert_call_args = mock_db_class.insert_many.call_args[0][0]
        assert len(insert_call_args) == 1


@pytest.mark.asyncio
async def test_create_crons_keeps_same_expression_different_timezones():
    """Test create_crons keeps triggers with same expression but different timezones"""
    graph_template = MagicMock()
    graph_template.name = "test_graph"
    graph_template.namespace = "test_ns"
    graph_template.triggers = [
        Trigger(
            value=make_trigger_value("0 9 * * *", "America/New_York")
        ),
        Trigger(
            value=make_trigger_value("0 9 * * *", "Europe/London")
        )
    ]

    with patch('app.tasks.verify_graph.DatabaseTriggers') as mock_db_class:
        mock_db_class.return_value = MagicMock()
        mock_db_class.insert_many = AsyncMock()

        await create_crons(graph_template)

        # Should create two DatabaseTriggers instances (different timezones)
        assert mock_db_class.call_count == 2

        # insert_many should be called with list of 2
        insert_call_args = mock_db_class.insert_many.call_args[0][0]
        assert len(insert_call_args) == 2


@pytest.mark.asyncio
async def test_create_crons_trigger_time_is_datetime():
    """Test that trigger_time is set to a datetime object"""
    graph_template = MagicMock()
    graph_template.name = "test_graph"
    graph_template.namespace = "test_ns"
    graph_template.triggers = [
        Trigger(
            value=make_trigger_value("0 9 * * *", "America/New_York")
        )
    ]

    with patch('app.tasks.verify_graph.DatabaseTriggers') as mock_db_class:
        mock_db_class.return_value = MagicMock()
        mock_db_class.insert_many = AsyncMock()

        await create_crons(graph_template)

        # Verify trigger_time is a datetime object
        call_kwargs = mock_db_class.call_args[1]
        assert isinstance(call_kwargs['trigger_time'], datetime)

