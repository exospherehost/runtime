"""
Tests for trigger_cron functions to improve code coverage.
These are pure unit tests that mock database operations.
Environment variables are provided by CI (see .github/workflows/test-state-manager.yml).
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
from pymongo.errors import DuplicateKeyError

from app.tasks.trigger_cron import (
    mark_as_triggered,
    mark_as_failed,
    get_due_triggers,
    call_trigger_graph,
    create_next_triggers,
    handle_trigger,
    trigger_cron
)
from app.models.db.trigger import DatabaseTriggers
from app.models.trigger_models import TriggerStatusEnum


@pytest.mark.asyncio
async def test_create_next_triggers_with_america_new_york_timezone():
    """Test create_next_triggers processes America/New_York timezone correctly"""
    trigger = MagicMock()
    trigger.expression = "0 9 * * *"
    trigger.timezone = "America/New_York"
    trigger.trigger_time = datetime(2025, 10, 4, 13, 0, 0)  # Naive UTC time
    trigger.graph_name = "test_graph"
    trigger.namespace = "test_namespace"

    cron_time = datetime(2025, 10, 6, 0, 0, 0)

    with patch('app.tasks.trigger_cron.DatabaseTriggers') as mock_db_class:
        mock_instance = MagicMock()
        mock_instance.insert = AsyncMock()
        mock_db_class.return_value = mock_instance

        await create_next_triggers(trigger, cron_time, 24)

        # Verify DatabaseTriggers was instantiated with timezone
        assert mock_db_class.called
        call_kwargs = mock_db_class.call_args[1]
        assert call_kwargs['timezone'] == "America/New_York"
        assert call_kwargs['expression'] == "0 9 * * *"


@pytest.mark.asyncio
async def test_create_next_triggers_with_utc_timezone():
    """Test create_next_triggers with UTC timezone"""
    trigger = MagicMock()
    trigger.expression = "0 9 * * *"
    trigger.timezone = "UTC"
    trigger.trigger_time = datetime(2025, 10, 4, 9, 0, 0)
    trigger.graph_name = "test_graph"
    trigger.namespace = "test_namespace"

    cron_time = datetime(2025, 10, 6, 0, 0, 0)

    with patch('app.tasks.trigger_cron.DatabaseTriggers') as mock_db_class:
        mock_instance = MagicMock()
        mock_instance.insert = AsyncMock()
        mock_db_class.return_value = mock_instance

        await create_next_triggers(trigger, cron_time, 24)

        # Verify timezone was passed correctly
        call_kwargs = mock_db_class.call_args[1]
        assert call_kwargs['timezone'] == "UTC"


@pytest.mark.asyncio
async def test_create_next_triggers_with_none_timezone_defaults_to_utc():
    """Test create_next_triggers with None timezone defaults to UTC"""
    trigger = MagicMock()
    trigger.expression = "0 9 * * *"
    trigger.timezone = None
    trigger.trigger_time = datetime(2025, 10, 4, 9, 0, 0)
    trigger.graph_name = "test_graph"
    trigger.namespace = "test_namespace"

    cron_time = datetime(2025, 10, 6, 0, 0, 0)

    with patch('app.tasks.trigger_cron.DatabaseTriggers') as mock_db_class:
        mock_instance = MagicMock()
        mock_instance.insert = AsyncMock()
        mock_db_class.return_value = mock_instance

        await create_next_triggers(trigger, cron_time, 24)

        # Verify None timezone is passed through (will default to UTC in ZoneInfo call)
        call_kwargs = mock_db_class.call_args[1]
        assert call_kwargs['timezone'] is None


@pytest.mark.asyncio
async def test_create_next_triggers_with_europe_london_timezone():
    """Test create_next_triggers with Europe/London timezone"""
    trigger = MagicMock()
    trigger.expression = "0 17 * * *"
    trigger.timezone = "Europe/London"
    trigger.trigger_time = datetime(2025, 10, 4, 16, 0, 0)  # UTC time
    trigger.graph_name = "test_graph"
    trigger.namespace = "test_namespace"

    cron_time = datetime(2025, 10, 6, 0, 0, 0)

    with patch('app.tasks.trigger_cron.DatabaseTriggers') as mock_db_class:
        mock_instance = MagicMock()
        mock_instance.insert = AsyncMock()
        mock_db_class.return_value = mock_instance

        await create_next_triggers(trigger, cron_time, 24)

        # Verify Europe/London timezone was used
        call_kwargs = mock_db_class.call_args[1]
        assert call_kwargs['timezone'] == "Europe/London"

"""
Tests for trigger TTL (Time To Live) expiration logic.
Verifies that completed/failed triggers are properly marked for cleanup.
"""
@pytest.mark.asyncio
@pytest.mark.parametrize("mark_function,expected_status", [
    (mark_as_triggered, TriggerStatusEnum.TRIGGERED),
    (mark_as_failed, TriggerStatusEnum.FAILED),
])
async def test_mark_trigger_sets_expires_at(mark_function, expected_status):
    """Test that marking a trigger sets the expires_at field correctly"""
    # Create a mock trigger
    trigger = MagicMock(spec=DatabaseTriggers)
    trigger.id = "test_trigger_id"

    # Mock the database update
    with patch.object(DatabaseTriggers, 'get_pymongo_collection') as mock_collection:
        mock_collection.return_value.update_one = AsyncMock()

        # Call the function with retention_hours parameter
        await mark_function(trigger, retention_hours=24)

        # Verify update_one was called
        assert mock_collection.return_value.update_one.called
        call_args = mock_collection.return_value.update_one.call_args

        # Verify the filter (first argument)
        assert call_args[0][0] == {"_id": trigger.id}

        # Verify the update includes both status and expires_at
        update_dict = call_args[0][1]["$set"]
        assert update_dict["trigger_status"] == expected_status
        assert "expires_at" in update_dict

        # Verify expires_at is approximately 24 hours from now (UTC)
        expires_at = update_dict["expires_at"]
        expected_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 2  # Within 2 seconds tolerance

        # Verify expires_at is timezone-aware UTC
        assert expires_at.tzinfo is not None
        assert expires_at.tzinfo == timezone.utc


@pytest.mark.asyncio
@pytest.mark.parametrize("mark_function,retention_hours", [
    (mark_as_triggered, 12),
    (mark_as_triggered, 24),
    (mark_as_triggered, 48),
    (mark_as_failed, 12),
    (mark_as_failed, 24),
    (mark_as_failed, 48),
])
async def test_mark_trigger_uses_custom_retention_period(mark_function, retention_hours):
    """Test that custom retention period is respected across all mark functions"""
    # Create a mock trigger
    trigger = MagicMock(spec=DatabaseTriggers)
    trigger.id = "test_trigger_id"

    # Mock the database update
    with patch.object(DatabaseTriggers, 'get_pymongo_collection') as mock_collection:
        mock_collection.return_value.update_one = AsyncMock()

        # Call the function with custom retention period
        await mark_function(trigger, retention_hours=retention_hours)

        # Verify expires_at is approximately retention_hours from now (UTC)
        call_args = mock_collection.return_value.update_one.call_args
        update_dict = call_args[0][1]["$set"]
        expires_at = update_dict["expires_at"]
        expected_expiry = datetime.now(timezone.utc) + timedelta(hours=retention_hours)
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 2  # Within 2 seconds tolerance

        # Verify expires_at is timezone-aware UTC
        assert expires_at.tzinfo is not None
        assert expires_at.tzinfo == timezone.utc

@pytest.mark.asyncio
async def test_get_due_triggers_returns_trigger():
    """Test get_due_triggers returns a PENDING trigger"""
    cron_time = datetime.now(timezone.utc)

    with patch.object(DatabaseTriggers, 'get_pymongo_collection') as mock_collection:
        with patch.object(DatabaseTriggers, '__init__', return_value=None):
            mock_collection.return_value.find_one_and_update = AsyncMock(return_value={"_id": "trigger_id"})

            result = await get_due_triggers(cron_time)

            # Verify the query
            call_args = mock_collection.return_value.find_one_and_update.call_args
            assert call_args[0][0] == {
                "trigger_time": {"$lte": cron_time},
                "trigger_status": TriggerStatusEnum.PENDING
            }
            assert call_args[0][1] == {"$set": {"trigger_status": TriggerStatusEnum.TRIGGERING}}

            # Verify result is not None (data was returned)
            assert result is not None


@pytest.mark.asyncio
async def test_get_due_triggers_returns_none_when_no_triggers():
    """Test get_due_triggers returns None when no triggers are due"""
    cron_time = datetime.now(timezone.utc)

    with patch.object(DatabaseTriggers, 'get_pymongo_collection') as mock_collection:
        mock_collection.return_value.find_one_and_update = AsyncMock(return_value=None)

        result = await get_due_triggers(cron_time)

        assert result is None


@pytest.mark.asyncio
async def test_call_trigger_graph():
    """Test call_trigger_graph calls trigger_graph controller"""
    trigger = MagicMock(spec=DatabaseTriggers)
    trigger.namespace = "test_ns"
    trigger.graph_name = "test_graph"

    with patch('app.tasks.trigger_cron.trigger_graph') as mock_trigger_graph:
        mock_trigger_graph.return_value = AsyncMock()

        await call_trigger_graph(trigger)

        # Verify trigger_graph was called with correct parameters
        mock_trigger_graph.assert_called_once()
        call_kwargs = mock_trigger_graph.call_args.kwargs
        assert call_kwargs['namespace_name'] == "test_ns"
        assert call_kwargs['graph_name'] == "test_graph"
        assert 'body' in call_kwargs
        assert 'x_exosphere_request_id' in call_kwargs


@pytest.mark.asyncio
async def test_create_next_triggers_creates_future_trigger():
    """Test create_next_triggers creates next trigger in the future"""
    cron_time = datetime.now(timezone.utc).replace(tzinfo=None)
    trigger = MagicMock(spec=DatabaseTriggers)
    trigger.expression = "0 9 * * *"
    trigger.timezone = "UTC"
    trigger.trigger_time = cron_time - timedelta(days=1)
    trigger.graph_name = "test_graph"
    trigger.namespace = "test_ns"

    with patch('app.tasks.trigger_cron.DatabaseTriggers') as MockDatabaseTriggers:
        mock_instance = MagicMock()
        mock_instance.insert = AsyncMock()
        MockDatabaseTriggers.return_value = mock_instance

        await create_next_triggers(trigger, cron_time, 24)

        # Verify at least one trigger was created
        assert MockDatabaseTriggers.called
        assert mock_instance.insert.called


@pytest.mark.asyncio
async def test_create_next_triggers_handles_duplicate_key_error():
    """Test create_next_triggers handles DuplicateKeyError gracefully"""
    trigger = MagicMock()
    trigger.expression = "0 9 * * *"
    trigger.timezone = "America/New_York"
    trigger.trigger_time = datetime(2025, 10, 4, 13, 0, 0)
    trigger.graph_name = "test_graph"
    trigger.namespace = "test_namespace"

    cron_time = datetime(2025, 10, 6, 0, 0, 0)

    with patch('app.tasks.trigger_cron.DatabaseTriggers') as mock_db_class:
        mock_instance = MagicMock()
        # First call raises DuplicateKeyError, second succeeds
        mock_instance.insert = AsyncMock(side_effect=[
            DuplicateKeyError("Duplicate"),
            None
        ])
        mock_db_class.return_value = mock_instance

        with patch('app.tasks.trigger_cron.logger') as mock_logger:
            # Should not raise exception
            await create_next_triggers(trigger, cron_time, 24)

            # Verify error was logged
            assert mock_logger.error.called
            error_msg = mock_logger.error.call_args[0][0]
            assert "Duplicate trigger found" in error_msg


@pytest.mark.asyncio
async def test_create_next_triggers_trigger_time_is_datetime():
    """Test that next trigger_time is a datetime object"""
    trigger = MagicMock()
    trigger.expression = "0 9 * * *"
    trigger.timezone = "America/New_York"
    trigger.trigger_time = datetime(2025, 10, 4, 13, 0, 0)
    trigger.graph_name = "test_graph"
    trigger.namespace = "test_namespace"

    cron_time = datetime(2025, 10, 6, 0, 0, 0)

    with patch('app.tasks.trigger_cron.DatabaseTriggers') as mock_db_class:
        mock_instance = MagicMock()
        mock_instance.insert = AsyncMock()
        mock_db_class.return_value = mock_instance

        await create_next_triggers(trigger, cron_time, 24)

        # Verify trigger_time is a datetime
        call_kwargs = mock_db_class.call_args[1]
        assert isinstance(call_kwargs['trigger_time'], datetime)


@pytest.mark.asyncio
async def test_create_next_triggers_creates_multiple_triggers():
    """Test create_next_triggers creates multiple future triggers"""
    trigger = MagicMock()
    trigger.expression = "0 */6 * * *"  # Every 6 hours
    trigger.timezone = "UTC"
    trigger.trigger_time = datetime(2025, 10, 4, 0, 0, 0)
    trigger.graph_name = "test_graph"
    trigger.namespace = "test_namespace"

    cron_time = datetime(2025, 10, 5, 0, 0, 0)  # 24 hours later

    with patch('app.tasks.trigger_cron.DatabaseTriggers') as mock_db_class:
        mock_instance = MagicMock()
        mock_instance.insert = AsyncMock()
        mock_db_class.return_value = mock_instance

        await create_next_triggers(trigger, cron_time, 24)

        # Should create multiple triggers (every 6 hours until past cron_time)
        assert mock_db_class.call_count >= 4  # At least 4 triggers in 24 hours


@pytest.mark.asyncio
async def test_create_next_triggers_raises_on_other_exceptions():
    """Test create_next_triggers raises on non-DuplicateKeyError exceptions"""
    cron_time = datetime.now(timezone.utc).replace(tzinfo=None)
    trigger = MagicMock(spec=DatabaseTriggers)
    trigger.expression = "0 9 * * *"
    trigger.timezone = "UTC"
    trigger.trigger_time = cron_time - timedelta(days=1)
    trigger.graph_name = "test_graph"
    trigger.namespace = "test_ns"

    with patch('app.tasks.trigger_cron.DatabaseTriggers') as MockDatabaseTriggers:
        mock_instance = MagicMock()
        mock_instance.insert = AsyncMock(side_effect=ValueError("test error"))
        MockDatabaseTriggers.return_value = mock_instance

        with pytest.raises(ValueError, match="test error"):
            await create_next_triggers(trigger, cron_time, 24)


@pytest.mark.asyncio
async def test_handle_trigger_success_path():
    """Test handle_trigger processes trigger successfully"""
    cron_time = datetime.now(timezone.utc)
    trigger = MagicMock(spec=DatabaseTriggers)
    trigger.id = "trigger_id"
    trigger.expression = "0 9 * * *"
    trigger.trigger_time = cron_time - timedelta(days=1)
    trigger.graph_name = "test_graph"
    trigger.namespace = "test_ns"

    with patch('app.tasks.trigger_cron.get_due_triggers') as mock_get_due:
        with patch('app.tasks.trigger_cron.call_trigger_graph') as mock_call:
            with patch('app.tasks.trigger_cron.mark_as_triggered') as mock_mark_triggered:
                with patch('app.tasks.trigger_cron.create_next_triggers') as mock_create_next:
                    # Return trigger once, then None to stop loop
                    mock_get_due.side_effect = [trigger, None]
                    mock_call.return_value = AsyncMock()
                    mock_mark_triggered.return_value = AsyncMock()
                    mock_create_next.return_value = AsyncMock()

                    await handle_trigger(cron_time, retention_hours=24)

                    # Verify all functions were called
                    assert mock_call.called
                    assert mock_mark_triggered.called
                    assert mock_create_next.called


@pytest.mark.asyncio
async def test_handle_trigger_failure_path():
    """Test handle_trigger marks trigger as failed on exception"""
    cron_time = datetime.now(timezone.utc)
    trigger = MagicMock(spec=DatabaseTriggers)
    trigger.id = "trigger_id"
    trigger.expression = "0 9 * * *"
    trigger.trigger_time = cron_time - timedelta(days=1)
    trigger.graph_name = "test_graph"
    trigger.namespace = "test_ns"

    with patch('app.tasks.trigger_cron.get_due_triggers') as mock_get_due:
        with patch('app.tasks.trigger_cron.call_trigger_graph') as mock_call:
            with patch('app.tasks.trigger_cron.mark_as_failed') as mock_mark_failed:
                with patch('app.tasks.trigger_cron.create_next_triggers') as mock_create_next:
                    # Return trigger once, then None
                    mock_get_due.side_effect = [trigger, None]
                    mock_call.side_effect = Exception("Trigger failed")
                    mock_mark_failed.return_value = AsyncMock()
                    mock_create_next.return_value = AsyncMock()

                    await handle_trigger(cron_time, retention_hours=24)

                    # Verify mark_as_failed was called
                    mock_mark_failed.assert_called_once_with(trigger, 24)
                    # Verify create_next_triggers was still called (finally block)
                    assert mock_create_next.called


@pytest.mark.asyncio
async def test_trigger_cron():
    """Test trigger_cron orchestrates handle_trigger with settings"""
    with patch('app.tasks.trigger_cron.get_settings') as mock_get_settings:
        with patch('app.tasks.trigger_cron.handle_trigger') as mock_handle:
            mock_settings = MagicMock()
            mock_settings.trigger_retention_hours = 24
            mock_settings.trigger_workers = 2
            mock_get_settings.return_value = mock_settings
            mock_handle.return_value = AsyncMock()

            await trigger_cron()

            # Verify handle_trigger was called correct number of times
            assert mock_handle.call_count == 2
            # Verify retention_hours parameter was passed
            for call in mock_handle.call_args_list:
                assert call[0][1] == 24  # retention_hours
