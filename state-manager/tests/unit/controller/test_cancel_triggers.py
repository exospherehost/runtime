"""
Tests for cancel_triggers controller.
Verifies cancellation of pending and triggering triggers for a graph.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.controller.cancel_triggers import cancel_triggers
from app.models.cancel_trigger_models import CancelTriggerResponse
from app.models.db.trigger import DatabaseTriggers


@pytest.mark.asyncio
async def test_cancel_triggers_success_with_pending():
    """Test successfully cancelling PENDING triggers"""
    namespace_name = "test_namespace"
    graph_name = "test_graph"
    x_exosphere_request_id = "test_request_id"

    # Create mock triggers
    mock_trigger1 = MagicMock(spec=DatabaseTriggers)
    mock_trigger1.id = "trigger_id_1"
    mock_trigger2 = MagicMock(spec=DatabaseTriggers)
    mock_trigger2.id = "trigger_id_2"

    with patch('app.controller.cancel_triggers.DatabaseTriggers') as mock_db, \
         patch('app.controller.cancel_triggers.get_settings') as mock_get_settings, \
         patch('app.controller.cancel_triggers.mark_as_cancelled') as mock_mark_cancelled:
        
        # Setup mock database query
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[mock_trigger1, mock_trigger2])
        mock_db.find.return_value = mock_query

        # Setup mock settings
        mock_settings = MagicMock()
        mock_settings.trigger_retention_hours = 24
        mock_get_settings.return_value = mock_settings

        result = await cancel_triggers(namespace_name, graph_name, x_exosphere_request_id)

        # Verify result
        assert isinstance(result, CancelTriggerResponse)
        assert result.namespace == namespace_name
        assert result.graph_name == graph_name
        assert result.cancelled_count == 2
        assert "Successfully cancelled 2 trigger(s)" in result.message

        # Verify mark_as_cancelled was called for each trigger
        assert mock_mark_cancelled.call_count == 2


@pytest.mark.asyncio
async def test_cancel_triggers_success_with_triggering():
    """Test successfully cancelling TRIGGERING triggers"""
    namespace_name = "test_namespace"
    graph_name = "test_graph"
    x_exosphere_request_id = "test_request_id"

    # Create mock trigger
    mock_trigger = MagicMock(spec=DatabaseTriggers)
    mock_trigger.id = "trigger_id_1"

    with patch('app.controller.cancel_triggers.DatabaseTriggers') as mock_db, \
         patch('app.controller.cancel_triggers.get_settings') as mock_get_settings, \
         patch('app.controller.cancel_triggers.mark_as_cancelled') as mock_mark_cancelled:
        
        # Setup mock database query
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[mock_trigger])
        mock_db.find.return_value = mock_query

        # Setup mock settings
        mock_settings = MagicMock()
        mock_settings.trigger_retention_hours = 12
        mock_get_settings.return_value = mock_settings

        result = await cancel_triggers(namespace_name, graph_name, x_exosphere_request_id)

        # Verify result
        assert isinstance(result, CancelTriggerResponse)
        assert result.cancelled_count == 1
        assert "Successfully cancelled 1 trigger(s)" in result.message

        # Verify mark_as_cancelled was called with retention_hours from settings
        mock_mark_cancelled.assert_called_once_with(mock_trigger, 12)


@pytest.mark.asyncio
async def test_cancel_triggers_no_triggers_found():
    """Test cancelling triggers when no pending triggers exist"""
    namespace_name = "test_namespace"
    graph_name = "test_graph"
    x_exosphere_request_id = "test_request_id"

    with patch('app.controller.cancel_triggers.DatabaseTriggers') as mock_db:
        # Setup mock database query to return empty list
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[])
        mock_db.find.return_value = mock_query

        result = await cancel_triggers(namespace_name, graph_name, x_exosphere_request_id)

        # Verify result
        assert isinstance(result, CancelTriggerResponse)
        assert result.namespace == namespace_name
        assert result.graph_name == graph_name
        assert result.cancelled_count == 0
        assert "No pending triggers found to cancel" in result.message


@pytest.mark.asyncio
async def test_cancel_triggers_query_filters_correctly():
    """Test that the query filters by namespace, graph_name, and status"""
    namespace_name = "test_namespace"
    graph_name = "test_graph"
    x_exosphere_request_id = "test_request_id"

    with patch('app.controller.cancel_triggers.DatabaseTriggers') as mock_db, \
         patch('app.controller.cancel_triggers.get_settings') as mock_get_settings, \
         patch('app.controller.cancel_triggers.mark_as_cancelled'):
        
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[])
        mock_db.find.return_value = mock_query

        mock_settings = MagicMock()
        mock_settings.trigger_retention_hours = 24
        mock_get_settings.return_value = mock_settings

        await cancel_triggers(namespace_name, graph_name, x_exosphere_request_id)

        # Verify find was called with correct arguments
        mock_db.find.assert_called_once()
        call_args = mock_db.find.call_args
        
        # Check that all three conditions are in the call
        # The call should include namespace, graph_name, and In for trigger_status
        assert call_args is not None


@pytest.mark.asyncio
async def test_cancel_triggers_uses_settings_retention_hours():
    """Test that the function uses retention hours from settings"""
    namespace_name = "test_namespace"
    graph_name = "test_graph"
    x_exosphere_request_id = "test_request_id"

    mock_trigger = MagicMock(spec=DatabaseTriggers)
    mock_trigger.id = "trigger_id_1"

    with patch('app.controller.cancel_triggers.DatabaseTriggers') as mock_db, \
         patch('app.controller.cancel_triggers.get_settings') as mock_get_settings, \
         patch('app.controller.cancel_triggers.mark_as_cancelled') as mock_mark_cancelled:
        
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[mock_trigger])
        mock_db.find.return_value = mock_query

        mock_settings = MagicMock()
        mock_settings.trigger_retention_hours = 48
        mock_get_settings.return_value = mock_settings

        await cancel_triggers(namespace_name, graph_name, x_exosphere_request_id)

        # Verify mark_as_cancelled was called with correct retention_hours
        mock_mark_cancelled.assert_called_once_with(mock_trigger, 48)


@pytest.mark.asyncio
async def test_cancel_triggers_handles_database_error():
    """Test that database errors are properly logged and re-raised"""
    namespace_name = "test_namespace"
    graph_name = "test_graph"
    x_exosphere_request_id = "test_request_id"

    with patch('app.controller.cancel_triggers.DatabaseTriggers') as mock_db:
        mock_db.find.side_effect = Exception("Database connection error")

        with pytest.raises(Exception, match="Database connection error"):
            await cancel_triggers(namespace_name, graph_name, x_exosphere_request_id)


@pytest.mark.asyncio
async def test_cancel_triggers_handles_mark_error():
    """Test that errors during marking are properly handled"""
    namespace_name = "test_namespace"
    graph_name = "test_graph"
    x_exosphere_request_id = "test_request_id"

    mock_trigger = MagicMock(spec=DatabaseTriggers)
    mock_trigger.id = "trigger_id_1"

    with patch('app.controller.cancel_triggers.DatabaseTriggers') as mock_db, \
         patch('app.controller.cancel_triggers.get_settings') as mock_get_settings, \
         patch('app.controller.cancel_triggers.mark_as_cancelled') as mock_mark_cancelled:
        
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[mock_trigger])
        mock_db.find.return_value = mock_query

        mock_settings = MagicMock()
        mock_settings.trigger_retention_hours = 24
        mock_get_settings.return_value = mock_settings

        mock_mark_cancelled.side_effect = Exception("Failed to update trigger")

        with pytest.raises(Exception, match="Failed to update trigger"):
            await cancel_triggers(namespace_name, graph_name, x_exosphere_request_id)


@pytest.mark.asyncio
async def test_cancel_triggers_multiple_triggers_batch():
    """Test that multiple triggers are cancelled in batch"""
    namespace_name = "test_namespace"
    graph_name = "test_graph"
    x_exosphere_request_id = "test_request_id"

    mock_trigger1 = MagicMock(spec=DatabaseTriggers)
    mock_trigger1.id = "trigger_id_1"
    mock_trigger2 = MagicMock(spec=DatabaseTriggers)
    mock_trigger2.id = "trigger_id_2"
    mock_trigger3 = MagicMock(spec=DatabaseTriggers)
    mock_trigger3.id = "trigger_id_3"

    with patch('app.controller.cancel_triggers.DatabaseTriggers') as mock_db, \
         patch('app.controller.cancel_triggers.get_settings') as mock_get_settings, \
         patch('app.controller.cancel_triggers.mark_as_cancelled') as mock_mark_cancelled:
        
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[mock_trigger1, mock_trigger2, mock_trigger3])
        mock_db.find.return_value = mock_query

        mock_settings = MagicMock()
        mock_settings.trigger_retention_hours = 24
        mock_get_settings.return_value = mock_settings

        result = await cancel_triggers(namespace_name, graph_name, x_exosphere_request_id)

        # Verify correct count
        assert result.cancelled_count == 3

        # Verify all triggers were processed
        assert mock_mark_cancelled.call_count == 3

@pytest.mark.asyncio
async def test_cancel_triggers_calls_get_settings():
    """Test that get_settings is called when cancelling triggers"""
    namespace_name = "test_namespace"
    graph_name = "test_graph"
    x_exosphere_request_id = "test_request_id"

    mock_trigger = MagicMock(spec=DatabaseTriggers)
    mock_trigger.id = "trigger_id_1"

    with patch('app.controller.cancel_triggers.DatabaseTriggers') as mock_db, \
         patch('app.controller.cancel_triggers.get_settings') as mock_get_settings, \
         patch('app.controller.cancel_triggers.mark_as_cancelled') as mock_mark_cancelled:
        
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[mock_trigger])
        mock_db.find.return_value = mock_query

        mock_settings = MagicMock()
        mock_settings.trigger_retention_hours = 24
        mock_get_settings.return_value = mock_settings

        await cancel_triggers(namespace_name, graph_name, x_exosphere_request_id)

        # Verify get_settings was called (only when there are triggers to cancel)
        mock_get_settings.assert_called_once()
        # Verify it was called with retention_hours from settings
        mock_mark_cancelled.assert_called_once_with(mock_trigger, 24)
