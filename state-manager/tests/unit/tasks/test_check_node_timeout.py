import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.tasks.check_node_timeout import check_node_timeout
from app.models.state_status_enum import StateStatusEnum


@pytest.mark.asyncio
async def test_check_node_timeout_with_different_timeouts():
    """Test that nodes with different timeout_minutes are handled correctly"""
    
    # Mock current time (Unix timestamp in seconds: 1700000000 = Nov 14, 2023)
    current_time_ms = 1700000000 * 1000  # Convert to milliseconds
    
    # Create mock states with different timeouts
    state1 = MagicMock()
    state1.status = StateStatusEnum.QUEUED
    state1.queued_at = current_time_ms - (35 * 60 * 1000)  # 35 minutes ago
    state1.timeout_minutes = 30  # Should timeout (35 > 30)
    
    state2 = MagicMock()
    state2.status = StateStatusEnum.QUEUED
    state2.queued_at = current_time_ms - (25 * 60 * 1000)  # 25 minutes ago
    state2.timeout_minutes = 30  # Should NOT timeout (25 < 30)
    
    state3 = MagicMock()
    state3.status = StateStatusEnum.QUEUED
    state3.queued_at = current_time_ms - (45 * 60 * 1000)  # 45 minutes ago
    state3.timeout_minutes = None  # Use global setting (30 min)
    
    mock_states = [state1, state2, state3]
    
    # Mock settings
    mock_settings = MagicMock()
    mock_settings.node_timeout_minutes = 30  # Global setting
    
    with patch('app.tasks.check_node_timeout.State') as mock_state_class, \
         patch('app.tasks.check_node_timeout.get_settings', return_value=mock_settings), \
         patch('app.tasks.check_node_timeout.time.time', return_value=current_time_ms / 1000):
        
        # Mock State.find().to_list() to return our mock states
        mock_state_class.find.return_value.to_list = AsyncMock(return_value=mock_states)
        mock_state_class.save_all = AsyncMock()
        
        await check_node_timeout()
        
        # Verify state1 and state3 were marked as TIMEDOUT, but not state2
        assert state1.status == StateStatusEnum.TIMEDOUT
        assert state1.error == "Node execution timed out after 30 minutes"
        
        assert state2.status == StateStatusEnum.QUEUED  # Should remain QUEUED
        
        assert state3.status == StateStatusEnum.TIMEDOUT
        assert state3.error == "Node execution timed out after 30 minutes"
        
        # Verify save_all was called with the 2 timed out states
        mock_state_class.save_all.assert_called_once()
        saved_states = mock_state_class.save_all.call_args[0][0]
        assert len(saved_states) == 2
        assert state1 in saved_states
        assert state3 in saved_states


@pytest.mark.asyncio
async def test_check_node_timeout_no_timeouts():
    """Test that no states are marked as timed out when none exceed their timeout"""
    
    current_time_ms = 1700000000 * 1000
    
    # Create mock state that hasn't timed out
    state1 = MagicMock()
    state1.status = StateStatusEnum.QUEUED
    state1.queued_at = current_time_ms - (10 * 60 * 1000)  # 10 minutes ago
    state1.timeout_minutes = 30  # Should NOT timeout
    
    mock_states = [state1]
    mock_settings = MagicMock()
    mock_settings.node_timeout_minutes = 30
    
    with patch('app.tasks.check_node_timeout.State') as mock_state_class, \
         patch('app.tasks.check_node_timeout.get_settings', return_value=mock_settings), \
         patch('app.tasks.check_node_timeout.time.time', return_value=current_time_ms / 1000):
        
        mock_state_class.find.return_value.to_list = AsyncMock(return_value=mock_states)
        mock_state_class.save_all = AsyncMock()
        
        await check_node_timeout()
        
        # Verify state remains QUEUED
        assert state1.status == StateStatusEnum.QUEUED
        
        # Verify save_all was not called since no states timed out
        mock_state_class.save_all.assert_not_called()


@pytest.mark.asyncio
async def test_check_node_timeout_handles_exception():
    """Test that exceptions in check_node_timeout are logged properly"""
    
    with patch('app.tasks.check_node_timeout.State') as mock_state_class, \
         patch('app.tasks.check_node_timeout.logger') as mock_logger:
        
        # Mock State.find to raise an exception
        mock_state_class.find.side_effect = Exception("Database error")
        
        await check_node_timeout()
        
        # Verify error was logged with exc_info
        mock_logger.error.assert_called_once_with("Error checking node timeout", exc_info=True)


@pytest.mark.asyncio
async def test_check_node_timeout_custom_node_timeout():
    """Test that nodes with custom timeout_minutes use their own timeout value"""
    
    current_time_ms = 1700000000 * 1000
    
    # Create mock state with custom timeout
    state1 = MagicMock()
    state1.status = StateStatusEnum.QUEUED
    state1.queued_at = current_time_ms - (35 * 60 * 1000)  # 35 minutes ago
    state1.timeout_minutes = 60  # Custom timeout of 60 minutes - should NOT timeout
    
    # Create mock state with global timeout
    state2 = MagicMock()
    state2.status = StateStatusEnum.QUEUED
    state2.queued_at = current_time_ms - (35 * 60 * 1000)  # 35 minutes ago
    state2.timeout_minutes = None  # Use global setting (30 min) - should timeout
    
    mock_states = [state1, state2]
    mock_settings = MagicMock()
    mock_settings.node_timeout_minutes = 30  # Global setting
    
    with patch('app.tasks.check_node_timeout.State') as mock_state_class, \
         patch('app.tasks.check_node_timeout.get_settings', return_value=mock_settings), \
         patch('app.tasks.check_node_timeout.time.time', return_value=current_time_ms / 1000):
        
        mock_state_class.find.return_value.to_list = AsyncMock(return_value=mock_states)
        mock_state_class.save_all = AsyncMock()
        
        await check_node_timeout()
        
        # Verify only state2 was marked as TIMEDOUT (using global 30 min timeout)
        assert state1.status == StateStatusEnum.QUEUED  # Custom 60 min timeout
        
        assert state2.status == StateStatusEnum.TIMEDOUT  # Global 30 min timeout
        assert state2.error == "Node execution timed out after 30 minutes"
        
        # Verify save_all was called with only state2
        mock_state_class.save_all.assert_called_once()
        saved_states = mock_state_class.save_all.call_args[0][0]
        assert len(saved_states) == 1
        assert state2 in saved_states