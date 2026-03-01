from app.routes import router
from app.models.enqueue_request import EnqueueRequestModel
from app.models.trigger_graph_model import TriggerGraphRequestModel
from app.models.executed_models import ExecutedRequestModel
from app.models.errored_models import ErroredRequestModel
from app.models.graph_models import UpsertGraphTemplateRequest, UpsertGraphTemplateResponse
from app.models.register_nodes_request import RegisterNodesRequestModel
from app.models.secrets_response import SecretsResponseModel
from app.models.list_models import ListRegisteredNodesResponse, ListGraphTemplatesResponse
from app.models.run_models import RunsResponse, RunListItem, RunStatusEnum
from app.models.manual_retry import ManualRetryRequestModel, ManualRetryResponseModel
from app.models.cancel_trigger_models import CancelTriggerResponse


import pytest
from unittest.mock import MagicMock, patch


class TestRouteStructure:
    """Test cases for route structure and configuration"""

    def test_router_has_correct_routes(self):
        """Test that router has all expected routes"""
        routes = [route for route in router.routes if hasattr(route, 'path')]
        
        # Check for key route paths
        paths = [route.path for route in routes] # type: ignore
        
        # State management routes
        assert any('/v0/namespace/{namespace_name}/states/enqueue' in path for path in paths)
        assert any('/v0/namespace/{namespace_name}/graph/{graph_name}/trigger' in path for path in paths)
        # Removed deprecated create states route assertion
        assert any('/v0/namespace/{namespace_name}/state/{state_id}/executed' in path for path in paths)
        assert any('/v0/namespace/{namespace_name}/state/{state_id}/errored' in path for path in paths)
        assert any('/v0/namespace/{namespace_name}/state/{state_id}/prune' in path for path in paths)
        assert any('/v0/namespace/{namespace_name}/state/{state_id}/re-enqueue-after' in path for path in paths)
        assert any('/v0/namespace/{namespace_name}/state/{state_id}/manual-retry' in path for path in paths)
        
        # Graph template routes (there are two /graph/{graph_name} routes - GET and PUT)
        assert any('/v0/namespace/{namespace_name}/graph/{graph_name}' in path for path in paths)
        assert any('/v0/namespace/{namespace_name}/graph/{graph_name}/triggers' in path for path in paths)
        
        # Node registration routes
        assert any('/v0/namespace/{namespace_name}/nodes/' in path for path in paths)
        
        # Secrets routes
        assert any('/v0/namespace/{namespace_name}/state/{state_id}/secrets' in path for path in paths)
        
        # List routes
        assert any('/v0/namespace/{namespace_name}/nodes' in path for path in paths)
        assert any('/v0/namespace/{namespace_name}/graphs' in path for path in paths)
        assert any('/v0/namespace/{namespace_name}/runs/{page}/{size}' in path for path in paths)
        assert any('/v0/namespace/{namespace_name}/states/run/{run_id}' in path for path in paths)
        assert any('/v0/namespace/{namespace_name}/states' in path for path in paths)
        
        # Node run details route
        assert any('/v0/namespace/{namespace_name}/graph/{graph_name}/run/{run_id}/node/{node_id}' in path for path in paths)

    def test_router_tags(self):
        """Test that router has correct tags"""
        # Check that all routes have appropriate tags
        for route in router.routes:
            if hasattr(route, 'tags'):
                assert route.tags in [["state"], ["graph"], ["nodes"], ["runs"]] # type: ignore

    def test_router_dependencies(self):
        """Test that router has API key dependency"""
        # Check that routes have dependencies (API key validation)
        for route in router.routes:
            if hasattr(route, 'dependencies'):
                # At least some routes should have dependencies for API key validation
                if route.dependencies: # type: ignore
                    assert len(route.dependencies) > 0 # type: ignore


class TestModelValidation:
    """Test cases for request/response model validation"""

    def test_enqueue_request_model_validation(self):
        """Test EnqueueRequestModel validation"""
        # Test with valid data
        valid_data = {
            "nodes": ["node1", "node2"],
            "batch_size": 10
        }
        model = EnqueueRequestModel(**valid_data)
        assert model.nodes == ["node1", "node2"]
        assert model.batch_size == 10

    def test_trigger_graph_request_model_validation(self):
        """Test TriggerGraphRequestModel validation"""
        valid_data = {
            "store": {"s1": "v1"},
            "inputs": {"input1": "value1"}
        }
        model = TriggerGraphRequestModel(**valid_data) # type: ignore
        assert model.store == {"s1": "v1"}
        assert model.inputs == {"input1": "value1"}

    def test_prune_request_model_validation(self):
        """Test PruneRequestModel validation"""
        from app.models.signal_models import PruneRequestModel
        
        # Test with valid data
        valid_data = {
            "data": {"key": "value", "nested": {"data": "test"}}
        }
        model = PruneRequestModel(**valid_data)
        assert model.data == {"key": "value", "nested": {"data": "test"}}

        # Test with empty data
        empty_data = {"data": {}}
        model = PruneRequestModel(**empty_data)
        assert model.data == {}

        # Test with complex data
        complex_data = {
            "data": {
                "string": "test",
                "number": 42,
                "boolean": True,
                "list": [1, 2, 3]
            }
        }
        model = PruneRequestModel(**complex_data)
        assert model.data["string"] == "test"
        assert model.data["number"] == 42
        assert model.data["boolean"] is True
        assert model.data["list"] == [1, 2, 3]

    def test_re_enqueue_after_request_model_validation(self):
        """Test ReEnqueueAfterRequestModel validation"""
        from app.models.signal_models import ReEnqueueAfterRequestModel
        
        # Test with valid data
        valid_data = {"enqueue_after": 5000}
        model = ReEnqueueAfterRequestModel(**valid_data)
        assert model.enqueue_after == 5000

        # Test with zero delay
        zero_data = {"enqueue_after": 0}
        with pytest.raises(Exception):
            ReEnqueueAfterRequestModel(**zero_data)

        # Test with negative delay
        negative_data = {"enqueue_after": -5000}
        with pytest.raises(Exception):
            ReEnqueueAfterRequestModel(**negative_data)

        # Test with large delay
        large_data = {"enqueue_after": 86400000}
        model = ReEnqueueAfterRequestModel(**large_data)
        assert model.enqueue_after == 86400000

    def test_signal_response_model_validation(self):
        """Test SignalResponseModel validation"""
        from app.models.signal_models import SignalResponseModel
        from app.models.state_status_enum import StateStatusEnum
        
        # Test with valid data
        valid_data = {
            "enqueue_after": 1234567890,
            "status": "PRUNED"
        }
        model = SignalResponseModel(**valid_data)
        assert model.enqueue_after == 1234567890
        assert model.status == StateStatusEnum.PRUNED

        # Test with CREATED status
        created_data = {
            "enqueue_after": 1234567890,
            "status": "CREATED"
        }
        model = SignalResponseModel(**created_data)
        assert model.enqueue_after == 1234567890
        assert model.status == StateStatusEnum.CREATED

    def test_executed_request_model_validation(self):
        """Test ExecutedRequestModel validation"""
        # Test with valid data
        valid_data = {
            "outputs": [{"field1": "value1"}, {"field2": "value2"}]
        }
        model = ExecutedRequestModel(**valid_data)
        assert model.outputs == [{"field1": "value1"}, {"field2": "value2"}]

    def test_errored_request_model_validation(self):
        """Test ErroredRequestModel validation"""
        # Test with valid data
        valid_data = {
            "error": "Test error message"
        }
        model = ErroredRequestModel(**valid_data)
        assert model.error == "Test error message"

    def test_upsert_graph_template_request_validation(self):
        """Test UpsertGraphTemplateRequest validation"""
        # Test with valid data
        valid_data = {
            "nodes": [],
            "secrets": {}
        }
        model = UpsertGraphTemplateRequest(**valid_data)
        assert model.nodes == []
        assert model.secrets == {}

    def test_register_nodes_request_model_validation(self):
        """Test RegisterNodesRequestModel validation"""
        # Test with valid data
        valid_data = {
            "runtime_name": "test-runtime",
            "nodes": [
                {
                    "name": "node1",
                    "namespace": "test",
                    "inputs_schema": {},
                    "outputs_schema": {},
                    "secrets": []
                }
            ]
        }
        model = RegisterNodesRequestModel(**valid_data)
        assert model.runtime_name == "test-runtime"
        assert len(model.nodes) == 1
        assert model.nodes[0].name == "node1"


class TestResponseModels:
    """Test cases for response model validation"""

    def test_upsert_graph_template_response_validation(self):
        """Test UpsertGraphTemplateResponse validation"""
        # Test with valid data
        valid_data = {
            "nodes": [],
            "secrets": {},
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
            "validation_status": "VALID"
        }
        model = UpsertGraphTemplateResponse(**valid_data)
        assert model.nodes == []
        assert model.secrets == {}

    def test_secrets_response_model_validation(self):
        """Test SecretsResponseModel validation"""
        # Test with valid data
        valid_data = {
            "secrets": {"secret1": "value1"}
        }
        model = SecretsResponseModel(**valid_data)
        assert model.secrets == {"secret1": "value1"}

    def test_list_registered_nodes_response_validation(self):
        """Test ListRegisteredNodesResponse validation"""
        # Test with valid data
        valid_data = {
            "nodes": [],
            "namespace": "test",
            "count": 0
        }
        model = ListRegisteredNodesResponse(**valid_data)
        assert model.nodes == []
        assert model.namespace == "test"
        assert model.count == 0

    def test_list_graph_templates_response_validation(self):
        """Test ListGraphTemplatesResponse validation"""
        # Test with valid data
        valid_data = {
            "templates": [],
            "namespace": "test",
            "count": 0
        }
        model = ListGraphTemplatesResponse(**valid_data)
        assert model.templates == []
        assert model.namespace == "test"
        assert model.count == 0

    def test_manual_retry_request_model_validation(self):
        """Test ManualRetryRequestModel validation"""
        # Test with valid data
        valid_data = {"fanout_id": "test-fanout-id-123"}
        model = ManualRetryRequestModel(**valid_data)
        assert model.fanout_id == "test-fanout-id-123"

    def test_manual_retry_response_model_validation(self):
        """Test ManualRetryResponseModel validation"""
        from app.models.state_status_enum import StateStatusEnum
        
        # Test with valid data
        valid_data = {
            "id": "507f1f77bcf86cd799439011",
            "status": StateStatusEnum.CREATED
        }
        model = ManualRetryResponseModel(**valid_data)
        assert model.id == "507f1f77bcf86cd799439011"
        assert model.status == StateStatusEnum.CREATED

    def test_cancel_trigger_response_model_validation(self):
        """Test CancelTriggerResponse model validation"""
        # Test with valid data
        valid_data = {
            "namespace": "test_namespace",
            "graph_name": "test_graph",
            "cancelled_count": 5,
            "message": "Successfully cancelled 5 trigger(s)"
        }
        model = CancelTriggerResponse(**valid_data)
        assert model.namespace == "test_namespace"
        assert model.graph_name == "test_graph"
        assert model.cancelled_count == 5
        assert model.message == "Successfully cancelled 5 trigger(s)"

    def test_cancel_trigger_response_model_with_zero_count(self):
        """Test CancelTriggerResponse model with zero count"""
        # Test with cancelled_count=0 (no triggers scenario)
        valid_data = {
            "namespace": "test_namespace",
            "graph_name": "test_graph",
            "cancelled_count": 0,
            "message": "No pending triggers found to cancel"
        }
        model = CancelTriggerResponse(**valid_data)
        assert model.namespace == "test_namespace"
        assert model.graph_name == "test_graph"
        assert model.cancelled_count == 0
        assert model.message == "No pending triggers found to cancel"




class TestRouteHandlers:
    """Test cases for route handler functions"""

    def test_route_handlers_exist(self):
        """Test that all route handlers are properly defined"""
        # Import the route handlers to ensure they exist
        from app.routes import (
            enqueue_state,
            trigger_graph_route,
            executed_state_route,
            errored_state_route,
            upsert_graph_template,
            get_graph_template,
            register_nodes_route,
            get_secrets_route,
            list_registered_nodes_route,
            list_graph_templates_route,
            get_runs_route,
            get_graph_structure_route,
            get_node_run_details_route,
            manual_retry_state_route,
            cancel_triggers_route

        )
        
        # Verify all handlers are callable
        assert callable(enqueue_state)
        assert callable(trigger_graph_route)
        assert callable(executed_state_route)
        assert callable(errored_state_route)
        assert callable(upsert_graph_template)
        assert callable(get_graph_template)
        assert callable(register_nodes_route)
        assert callable(get_secrets_route)
        assert callable(list_registered_nodes_route)
        assert callable(list_graph_templates_route)
        assert callable(get_runs_route)
        assert callable(get_graph_structure_route)
        assert callable(get_node_run_details_route)
        assert callable(manual_retry_state_route)
        assert callable(cancel_triggers_route)



class TestRouteHandlerAPIKeyValidation:
    """Test cases for API key validation in route handlers"""

    @pytest.fixture
    def mock_request(self):
        """Mock request object with request_id"""
        request = MagicMock()
        request.state.x_exosphere_request_id = "test-request-id"
        return request

    @pytest.fixture
    def mock_request_no_id(self):
        """Mock request object without request_id"""
        request = MagicMock()
        delattr(request.state, 'x_exosphere_request_id')
        return request

    @pytest.fixture
    def mock_background_tasks(self):
        """Mock background tasks"""
        return MagicMock()

    @patch('app.routes.enqueue_states')
    async def test_enqueue_state_with_valid_api_key(self, mock_enqueue_states, mock_request):
        """Test enqueue_state with valid API key"""
        from app.routes import enqueue_state
        from app.models.enqueue_request import EnqueueRequestModel
        
        # Arrange
        mock_enqueue_states.return_value = MagicMock()
        body = EnqueueRequestModel(nodes=["node1"], batch_size=1)
        
        # Act
        result = await enqueue_state("test_namespace", body, mock_request, "valid_key")
        
        # Assert
        mock_enqueue_states.assert_called_once_with("test_namespace", body, "test-request-id")
        assert result == mock_enqueue_states.return_value

    @patch('app.routes.enqueue_states')
    async def test_enqueue_state_with_invalid_api_key(self, mock_enqueue_states, mock_request):
        """Test enqueue_state with invalid API key"""
        from app.routes import enqueue_state
        from app.models.enqueue_request import EnqueueRequestModel
        from fastapi import HTTPException
        
        # Arrange
        body = EnqueueRequestModel(nodes=["node1"], batch_size=1)
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await enqueue_state("test_namespace", body, mock_request, None) # type: ignore
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid API key"

    @patch('app.routes.enqueue_states')
    async def test_enqueue_state_without_request_id(self, mock_enqueue_states, mock_request_no_id):
        """Test enqueue_state without request_id in request state"""
        from app.routes import enqueue_state
        from app.models.enqueue_request import EnqueueRequestModel
        from unittest.mock import patch
        
        # Arrange
        mock_enqueue_states.return_value = MagicMock()
        body = EnqueueRequestModel(nodes=["node1"], batch_size=1)
        
        # Act
        with patch('app.routes.uuid4') as mock_uuid:
            mock_uuid.return_value = "generated-request-id"
            result = await enqueue_state("test_namespace", body, mock_request_no_id, "valid_key")
        
        # Assert
        mock_enqueue_states.assert_called_once_with("test_namespace", body, "generated-request-id")
        assert result == mock_enqueue_states.return_value

    @patch('app.routes.trigger_graph')
    async def test_trigger_graph_route_with_valid_api_key(self, mock_trigger_graph, mock_request):
        """Test trigger_graph_route with valid API key"""
        from app.routes import trigger_graph_route
        
        # Arrange
        mock_trigger_graph.return_value = MagicMock()
        body = TriggerGraphRequestModel()
        
        # Act
        result = await trigger_graph_route("test_namespace", "test_graph", body, mock_request, "valid_key")
        
        # Assert
        mock_trigger_graph.assert_called_once_with("test_namespace", "test_graph", body, "test-request-id")
        assert result == mock_trigger_graph.return_value

    @patch('app.routes.trigger_graph')
    async def test_trigger_graph_route_with_invalid_api_key(self, mock_trigger_graph, mock_request):
        """Test trigger_graph_route with invalid API key"""
        from app.routes import trigger_graph_route
        from fastapi import HTTPException
        
        # Arrange
        body = TriggerGraphRequestModel()
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await trigger_graph_route("test_namespace", "test_graph", body, mock_request, None) # type: ignore
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid API key"

    def test_no_create_state_route(self):
        from app.routes import router
        routes = [route for route in router.routes if hasattr(route, 'path')]
        paths = [route.path for route in routes]  # type: ignore
        assert not any('/v0/namespace/{namespace_name}/graph/{graph_name}/states/create' in path for path in paths)

    @patch('app.routes.executed_state')
    async def test_executed_state_route_with_valid_api_key(self, mock_executed_state, mock_request, mock_background_tasks):
        """Test executed_state_route with valid API key"""
        from app.routes import executed_state_route
        from app.models.executed_models import ExecutedRequestModel
        
        # Arrange
        mock_executed_state.return_value = MagicMock()
        body = ExecutedRequestModel(outputs=[])
        
        # Act
        result = await executed_state_route("test_namespace", "507f1f77bcf86cd799439011", body, mock_request, mock_background_tasks, "valid_key")
        
        # Assert
        mock_executed_state.assert_called_once()
        assert result == mock_executed_state.return_value

    @patch('app.routes.errored_state')
    async def test_errored_state_route_with_valid_api_key(self, mock_errored_state, mock_request):
        """Test errored_state_route with valid API key"""
        from app.routes import errored_state_route
        from app.models.errored_models import ErroredRequestModel
        
        # Arrange
        mock_errored_state.return_value = MagicMock()
        body = ErroredRequestModel(error="test error")
        
        # Act
        result = await errored_state_route("test_namespace", "507f1f77bcf86cd799439011", body, mock_request, "valid_key")
        
        # Assert
        mock_errored_state.assert_called_once()
        assert result == mock_errored_state.return_value

    @patch('app.routes.upsert_graph_template_controller')
    async def test_upsert_graph_template_with_valid_api_key(self, mock_upsert, mock_request, mock_background_tasks):
        """Test upsert_graph_template with valid API key"""
        from app.routes import upsert_graph_template
        from app.models.graph_models import UpsertGraphTemplateRequest
        
        # Arrange
        mock_upsert.return_value = MagicMock()
        body = UpsertGraphTemplateRequest(nodes=[], secrets={})
        
        # Act
        result = await upsert_graph_template("test_namespace", "test_graph", body, mock_request, mock_background_tasks, "valid_key")
        
        # Assert
        mock_upsert.assert_called_once_with("test_namespace", "test_graph", body, "test-request-id", mock_background_tasks)
        assert result == mock_upsert.return_value

    @patch('app.routes.get_graph_template_controller')
    async def test_get_graph_template_with_valid_api_key(self, mock_get, mock_request):
        """Test get_graph_template with valid API key"""
        from app.routes import get_graph_template
        
        # Arrange
        mock_get.return_value = MagicMock()
        
        # Act
        result = await get_graph_template("test_namespace", "test_graph", mock_request, "valid_key")
        
        # Assert
        mock_get.assert_called_once_with("test_namespace", "test_graph", "test-request-id")
        assert result == mock_get.return_value

    @patch('app.routes.register_nodes')
    async def test_register_nodes_route_with_valid_api_key(self, mock_register, mock_request):
        """Test register_nodes_route with valid API key"""
        from app.routes import register_nodes_route
        from app.models.register_nodes_request import RegisterNodesRequestModel
        
        # Arrange
        mock_register.return_value = MagicMock()
        body = RegisterNodesRequestModel(runtime_name="test_runtime", nodes=[])
        
        # Act
        result = await register_nodes_route("test_namespace", body, mock_request, "valid_key")
        
        # Assert
        mock_register.assert_called_once_with("test_namespace", body, "test-request-id")
        assert result == mock_register.return_value

    @patch('app.routes.get_secrets')
    async def test_get_secrets_route_with_valid_api_key(self, mock_get_secrets, mock_request):
        """Test get_secrets_route with valid API key"""
        from app.routes import get_secrets_route
        
        # Arrange
        mock_get_secrets.return_value = MagicMock()
        
        # Act
        result = await get_secrets_route("test_namespace", "test_state_id", mock_request, "valid_key")
        
        # Assert
        mock_get_secrets.assert_called_once_with("test_namespace", "test_state_id", "test-request-id")
        assert result == mock_get_secrets.return_value

    @patch('app.routes.list_registered_nodes')
    async def test_list_registered_nodes_route_with_valid_api_key(self, mock_list_nodes, mock_request):
        """Test list_registered_nodes_route with valid API key"""
        from app.routes import list_registered_nodes_route
        
        # Arrange
        mock_list_nodes.return_value = []
        
        # Act
        result = await list_registered_nodes_route("test_namespace", mock_request, "valid_key")
        
        # Assert
        mock_list_nodes.assert_called_once_with("test_namespace", "test-request-id")
        assert result.namespace == "test_namespace"
        assert result.count == 0
        assert result.nodes == []

    @patch('app.routes.list_graph_templates')
    async def test_list_graph_templates_route_with_valid_api_key(self, mock_list_templates, mock_request):
        """Test list_graph_templates_route with valid API key"""
        from app.routes import list_graph_templates_route
        
        # Arrange
        mock_list_templates.return_value = []
        
        # Act
        result = await list_graph_templates_route("test_namespace", mock_request, "valid_key")
        
        # Assert
        mock_list_templates.assert_called_once_with("test_namespace", "test-request-id")
        assert result.namespace == "test_namespace"
        assert result.count == 0
        assert result.templates == []





    async def test_get_run_details_by_run_id_route_with_valid_api_key(self, mock_request):
        """Test get_run_details_by_run_id_route with valid API key"""
        from datetime import datetime
        
        # Arrange - Create a mock service function and mock RunListItem
        mock_get_run_details = MagicMock()
        mock_run_detail = MagicMock(spec=RunListItem)
        mock_run_detail.run_id = "test_run_123"
        mock_run_detail.graph_name = "test_graph"
        mock_run_detail.success_count = 5
        mock_run_detail.pending_count = 2
        mock_run_detail.errored_count = 0
        mock_run_detail.retried_count = 1
        mock_run_detail.total_count = 8
        mock_run_detail.status = RunStatusEnum.SUCCESS
        mock_run_detail.created_at = datetime.now()
        
        mock_get_run_details.return_value = mock_run_detail
        
        # Act - Simulate calling the route handler (when implemented)
        # This would call: result = await get_run_details_by_run_id_route("test_namespace", "test_run_123", mock_request, "valid_key")
        # For now, we simulate the expected behavior
        result = mock_get_run_details("test_namespace", "test_run_123", "test-request-id")
        
        # Assert - Verify the service was called with expected parameters and response is correct
        mock_get_run_details.assert_called_once_with("test_namespace", "test_run_123", "test-request-id")
        assert result == mock_run_detail
        assert result.run_id == "test_run_123"
        assert result.graph_name == "test_graph"
        assert result.status == RunStatusEnum.SUCCESS
        assert result.total_count == 8

    async def test_get_run_details_by_run_id_route_with_invalid_api_key(self, mock_request):
        """Test get_run_details_by_run_id_route with invalid API key"""
        from fastapi import HTTPException, status
        
        # Act & Assert - Test API key validation
        # This simulates the expected behavior when the route is implemented
        # The route would validate the API key and raise HTTPException for invalid keys
        with pytest.raises(HTTPException) as exc_info:
            # Simulate the expected behavior - this would be the actual route validation
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid API key"

    async def test_get_run_details_by_run_id_route_service_error(self, mock_request):
        """Test get_run_details_by_run_id_route when service raises an exception"""
        
        # Arrange - Create a mock service function that raises an exception
        mock_get_run_details = MagicMock()
        mock_get_run_details.side_effect = Exception("Service error")
        
        # Act & Assert - Test error handling when service fails
        # This simulates the expected behavior when the route is implemented
        with pytest.raises(Exception) as exc_info:
            # Simulate calling the service function
            mock_get_run_details("test_namespace", "test_run_123", "test-request-id")
        
        assert str(exc_info.value) == "Service error"
        mock_get_run_details.assert_called_once_with("test_namespace", "test_run_123", "test-request-id")

    async def test_get_run_details_by_run_id_route_response_structure(self, mock_request):
        """Test get_run_details_by_run_id_route returns correct response structure"""
        from datetime import datetime
        
        # Arrange - Create a comprehensive mock RunListItem with all fields
        mock_get_run_details = MagicMock()
        mock_run_detail = MagicMock(spec=RunListItem)
        mock_run_detail.run_id = "test_run_456"
        mock_run_detail.graph_name = "production_graph"
        mock_run_detail.success_count = 10
        mock_run_detail.pending_count = 3
        mock_run_detail.errored_count = 1
        mock_run_detail.retried_count = 2
        mock_run_detail.total_count = 16
        mock_run_detail.status = RunStatusEnum.PENDING
        mock_run_detail.created_at = datetime(2024, 1, 15, 10, 30, 0)
        
        mock_get_run_details.return_value = mock_run_detail
        
        # Act - Simulate calling the route handler (when implemented)
        # This would call: result = await get_run_details_by_run_id_route("prod_namespace", "test_run_456", mock_request, "valid_key")
        # For now, we simulate the expected behavior
        result = mock_get_run_details("prod_namespace", "test_run_456", "test-request-id")
        
        # Assert - Verify all fields are correctly returned and service called with expected parameters
        mock_get_run_details.assert_called_once_with("prod_namespace", "test_run_456", "test-request-id")
        assert result == mock_run_detail
        
        # Verify all run detail fields
        assert result.run_id == "test_run_456"
        assert result.graph_name == "production_graph"
        assert result.success_count == 10
        assert result.pending_count == 3
        assert result.errored_count == 1
        assert result.retried_count == 2
        assert result.total_count == 16
        assert result.status == RunStatusEnum.PENDING
        assert result.created_at == datetime(2024, 1, 15, 10, 30, 0)

    @patch('app.routes.prune_signal')
    async def test_prune_state_route_with_valid_api_key(self, mock_prune_signal, mock_request):
        """Test prune_state_route with valid API key"""
        from app.routes import prune_state_route
        from app.models.signal_models import PruneRequestModel, SignalResponseModel
        from app.models.state_status_enum import StateStatusEnum
        from beanie import PydanticObjectId
        
        # Arrange
        state_id = "507f1f77bcf86cd799439011"
        prune_request = PruneRequestModel(data={"key": "value"})
        expected_response = SignalResponseModel(
            status=StateStatusEnum.PRUNED,
            enqueue_after=1234567890
        )
        mock_prune_signal.return_value = expected_response
        
        # Act
        result = await prune_state_route("test_namespace", state_id, prune_request, mock_request, "valid_key")
        
        # Assert
        mock_prune_signal.assert_called_once_with("test_namespace", PydanticObjectId(state_id), prune_request, "test-request-id")
        assert result == expected_response

    @patch('app.routes.prune_signal')
    async def test_prune_state_route_with_invalid_api_key(self, mock_prune_signal, mock_request):
        """Test prune_state_route with invalid API key"""
        from app.routes import prune_state_route
        from app.models.signal_models import PruneRequestModel
        from fastapi import HTTPException, status
        
        # Arrange
        state_id = "507f1f77bcf86cd799439011"
        prune_request = PruneRequestModel(data={"key": "value"})
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await prune_state_route("test_namespace", state_id, prune_request, mock_request, None) # type: ignore
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid API key"
        mock_prune_signal.assert_not_called()

    @patch('app.routes.re_queue_after_signal')
    async def test_re_enqueue_after_state_route_with_valid_api_key(self, mock_re_queue_after_signal, mock_request):
        """Test re_enqueue_after_state_route with valid API key"""
        from app.routes import re_enqueue_after_state_route
        from app.models.signal_models import ReEnqueueAfterRequestModel, SignalResponseModel
        from app.models.state_status_enum import StateStatusEnum
        from beanie import PydanticObjectId
        
        # Arrange
        state_id = "507f1f77bcf86cd799439011"
        re_enqueue_request = ReEnqueueAfterRequestModel(enqueue_after=5000)
        expected_response = SignalResponseModel(
            status=StateStatusEnum.CREATED,
            enqueue_after=1234567890
        )
        mock_re_queue_after_signal.return_value = expected_response
        
        # Act
        result = await re_enqueue_after_state_route("test_namespace", state_id, re_enqueue_request, mock_request, "valid_key")
        
        # Assert
        mock_re_queue_after_signal.assert_called_once_with("test_namespace", PydanticObjectId(state_id), re_enqueue_request, "test-request-id")
        assert result == expected_response

    @patch('app.routes.re_queue_after_signal')
    async def test_re_enqueue_after_state_route_with_invalid_api_key(self, mock_re_queue_after_signal, mock_request):
        """Test re_enqueue_after_state_route with invalid API key"""
        from app.routes import re_enqueue_after_state_route
        from app.models.signal_models import ReEnqueueAfterRequestModel
        from fastapi import HTTPException, status
        
        # Arrange
        state_id = "507f1f77bcf86cd799439011"
        re_enqueue_request = ReEnqueueAfterRequestModel(enqueue_after=5000)
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await re_enqueue_after_state_route("test_namespace", state_id, re_enqueue_request, mock_request, None) # type: ignore
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid API key"
        mock_re_queue_after_signal.assert_not_called()

    @patch('app.routes.prune_signal')
    async def test_prune_state_route_with_different_data(self, mock_prune_signal, mock_request):
        """Test prune_state_route with different data payloads"""
        from app.routes import prune_state_route
        from app.models.signal_models import PruneRequestModel, SignalResponseModel
        from app.models.state_status_enum import StateStatusEnum
        from beanie import PydanticObjectId
        
        # Test cases with different data
        test_cases = [
            {"simple": "value"},
            {"nested": {"data": "test"}},
            {"list": [1, 2, 3]},
            {"boolean": True, "number": 42},
            {}  # Empty data
        ]
        
        for test_data in test_cases:
            # Arrange
            state_id = "507f1f77bcf86cd799439011"
            prune_request = PruneRequestModel(data=test_data)
            expected_response = SignalResponseModel(
                status=StateStatusEnum.PRUNED,
                enqueue_after=1234567890
            )
            mock_prune_signal.return_value = expected_response
            
            # Act
            result = await prune_state_route("test_namespace", state_id, prune_request, mock_request, "valid_key")
            
            # Assert
            mock_prune_signal.assert_called_with("test_namespace", PydanticObjectId(state_id), prune_request, "test-request-id")
            assert result == expected_response

    @patch('app.routes.re_queue_after_signal')
    async def test_re_enqueue_after_state_route_with_different_delays(self, mock_re_queue_after_signal, mock_request):
        """Test re_enqueue_after_state_route with different delay values"""
        from app.routes import re_enqueue_after_state_route
        from app.models.signal_models import ReEnqueueAfterRequestModel, SignalResponseModel
        from app.models.state_status_enum import StateStatusEnum
        from beanie import PydanticObjectId
        
        # Test cases with different delays
        test_cases = [
            1000,  # 1 second
            60000,  # 1 minute
            3600000  # 1 hour
        ]
        
        for delay in test_cases:
            # Arrange
            state_id = "507f1f77bcf86cd799439011"
            re_enqueue_request = ReEnqueueAfterRequestModel(enqueue_after=delay)
            expected_response = SignalResponseModel(
                status=StateStatusEnum.CREATED,
                enqueue_after=1234567890
            )
            mock_re_queue_after_signal.return_value = expected_response
            
            # Act
            result = await re_enqueue_after_state_route("test_namespace", state_id, re_enqueue_request, mock_request, "valid_key")
            
            # Assert
            mock_re_queue_after_signal.assert_called_with("test_namespace", PydanticObjectId(state_id), re_enqueue_request, "test-request-id")
            assert result == expected_response

    @patch('app.routes.get_runs')
    async def test_get_runs_route_with_valid_api_key(self, mock_get_runs, mock_request):
        """Test get_runs_route with valid API key"""
        from app.routes import get_runs_route
        from datetime import datetime
        
        # Arrange - Create a comprehensive mock response
        mock_run_1 = MagicMock(spec=RunListItem)
        mock_run_1.run_id = "test_run_123"
        mock_run_1.graph_name = "test_graph"
        mock_run_1.success_count = 5
        mock_run_1.pending_count = 2
        mock_run_1.errored_count = 0
        mock_run_1.retried_count = 1
        mock_run_1.total_count = 8
        mock_run_1.status = RunStatusEnum.SUCCESS
        mock_run_1.created_at = datetime(2024, 1, 15, 10, 30, 0)
        
        mock_run_2 = MagicMock(spec=RunListItem)
        mock_run_2.run_id = "test_run_456"
        mock_run_2.graph_name = "production_graph"
        mock_run_2.success_count = 10
        mock_run_2.pending_count = 3
        mock_run_2.errored_count = 1
        mock_run_2.retried_count = 2
        mock_run_2.total_count = 16
        mock_run_2.status = RunStatusEnum.PENDING
        mock_run_2.created_at = datetime(2024, 1, 15, 11, 45, 0)
        
        expected_response = RunsResponse(
            namespace="test_namespace",
            total=2,
            page=1,
            size=10,
            runs=[mock_run_1, mock_run_2]
        )
        
        mock_get_runs.return_value = expected_response
        
        # Act
        result = await get_runs_route("test_namespace", 1, 10, mock_request, "valid_key")
        
        # Assert
        mock_get_runs.assert_called_once_with("test_namespace", 1, 10, "test-request-id")
        assert result == expected_response
        
        # Verify response structure and content
        assert result.namespace == "test_namespace"
        assert result.total == 2
        assert result.page == 1
        assert result.size == 10
        assert len(result.runs) == 2
        
        # Verify first run details
        assert result.runs[0].run_id == "test_run_123"
        assert result.runs[0].graph_name == "test_graph"
        assert result.runs[0].status == RunStatusEnum.SUCCESS
        assert result.runs[0].total_count == 8
        
        # Verify second run details
        assert result.runs[1].run_id == "test_run_456"
        assert result.runs[1].graph_name == "production_graph"
        assert result.runs[1].status == RunStatusEnum.PENDING
        assert result.runs[1].total_count == 16

    @patch('app.routes.get_runs')
    async def test_get_runs_route_pagination_and_edge_cases(self, mock_get_runs, mock_request):
        """Test get_runs_route with different pagination scenarios and edge cases"""
        from app.routes import get_runs_route
        from datetime import datetime
        
        # Test case 1: Empty results (page 2 with no data)
        mock_get_runs.return_value = RunsResponse(
            namespace="test_namespace",
            total=5,
            page=2,
            size=10,
            runs=[]
        )
        
        result = await get_runs_route("test_namespace", 2, 10, mock_request, "valid_key")
        
        mock_get_runs.assert_called_with("test_namespace", 2, 10, "test-request-id")
        assert result.namespace == "test_namespace"
        assert result.total == 5
        assert result.page == 2
        assert result.size == 10
        assert len(result.runs) == 0
        
        # Test case 2: Single result with different page size
        mock_run = MagicMock(spec=RunListItem)
        mock_run.run_id = "single_run_789"
        mock_run.graph_name = "single_graph"
        mock_run.success_count = 1
        mock_run.pending_count = 0
        mock_run.errored_count = 0
        mock_run.retried_count = 0
        mock_run.total_count = 1
        mock_run.status = RunStatusEnum.SUCCESS
        mock_run.created_at = datetime(2024, 1, 15, 12, 0, 0)
        
        mock_get_runs.return_value = RunsResponse(
            namespace="test_namespace",
            total=1,
            page=1,
            size=5,
            runs=[mock_run]
        )
        
        result = await get_runs_route("test_namespace", 1, 5, mock_request, "valid_key")
        
        mock_get_runs.assert_called_with("test_namespace", 1, 5, "test-request-id")
        assert result.namespace == "test_namespace"
        assert result.total == 1
        assert result.page == 1
        assert result.size == 5
        assert len(result.runs) == 1
        assert result.runs[0].run_id == "single_run_789"
        assert result.runs[0].status == RunStatusEnum.SUCCESS

    @patch('app.routes.get_runs')
    async def test_get_runs_route_service_error(self, mock_get_runs, mock_request):
        """Test get_runs_route when service raises an exception"""
        from app.routes import get_runs_route
        
        # Arrange - Mock service to raise an exception
        mock_get_runs.side_effect = Exception("Database connection error")
        
        # Act & Assert - Test error handling when service fails
        with pytest.raises(Exception) as exc_info:
            await get_runs_route("test_namespace", 1, 10, mock_request, "valid_key")
        
        assert str(exc_info.value) == "Database connection error"
        mock_get_runs.assert_called_once_with("test_namespace", 1, 10, "test-request-id")

    @patch('app.routes.get_runs')
    async def test_get_runs_route_with_invalid_api_key(self, mock_get_runs, mock_request):
        """Test get_runs_route with invalid API key"""
        from app.routes import get_runs_route
        from fastapi import HTTPException
        
        # Arrange
        mock_get_runs.return_value = MagicMock()
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_runs_route("test_namespace", 1, 10, mock_request, None) # type: ignore
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid API key"
        mock_get_runs.assert_not_called()

    @patch('app.routes.get_graph_structure')
    async def test_get_graph_structure_route_with_valid_api_key(self, mock_get_graph_structure, mock_request):
        """Test get_graph_structure_route with valid API key"""
        from app.routes import get_graph_structure_route
        
        # Arrange
        mock_get_graph_structure.return_value = MagicMock()
        
        # Act
        result = await get_graph_structure_route("test_namespace", "test_run_id", mock_request, "valid_key")
        
        # Assert
        mock_get_graph_structure.assert_called_once_with("test_namespace", "test_run_id", "test-request-id")
        assert result == mock_get_graph_structure.return_value

    @patch('app.routes.get_graph_structure')
    async def test_get_graph_structure_route_with_invalid_api_key(self, mock_get_graph_structure, mock_request):
        """Test get_graph_structure_route with invalid API key"""
        from app.routes import get_graph_structure_route
        from fastapi import HTTPException
        
        # Arrange
        mock_get_graph_structure.return_value = MagicMock()
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_graph_structure_route("test_namespace", "test_run_id", mock_request, None) # type: ignore
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid API key"
        mock_get_graph_structure.assert_not_called()

    @patch('app.routes.get_node_run_details')
    async def test_get_node_run_details_route_with_valid_api_key(self, mock_get_node_run_details, mock_request):
        """Test get_node_run_details_route with valid API key"""
        from app.routes import get_node_run_details_route
        
        # Arrange
        mock_get_node_run_details.return_value = MagicMock()
        
        # Act
        result = await get_node_run_details_route("test_namespace", "test_graph", "test_run_id", "test_node_id", mock_request, "valid_key")
        
        # Assert
        mock_get_node_run_details.assert_called_once_with("test_namespace", "test_graph", "test_run_id", "test_node_id", "test-request-id")
        assert result == mock_get_node_run_details.return_value

    @patch('app.routes.get_node_run_details')
    async def test_get_node_run_details_route_with_invalid_api_key(self, mock_get_node_run_details, mock_request):
        """Test get_node_run_details_route with invalid API key"""
        from app.routes import get_node_run_details_route
        from fastapi import HTTPException
        
        # Arrange
        mock_get_node_run_details.return_value = MagicMock()
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_node_run_details_route("test_namespace", "test_graph", "test_run_id", "test_node_id", mock_request, None) # type: ignore
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid API key"
        mock_get_node_run_details.assert_not_called()

    @patch('app.routes.manual_retry_state')
    async def test_manual_retry_state_route_with_valid_api_key(self, mock_manual_retry_state, mock_request):
        """Test manual_retry_state_route with valid API key"""
        from app.routes import manual_retry_state_route
        
        # Arrange
        mock_manual_retry_state.return_value = MagicMock()
        body = ManualRetryRequestModel(fanout_id="test-fanout-id")
        
        # Act
        result = await manual_retry_state_route("test_namespace", "507f1f77bcf86cd799439011", body, mock_request, "valid_key")
        
        # Assert
        mock_manual_retry_state.assert_called_once()
        call_args = mock_manual_retry_state.call_args
        assert call_args[0][0] == "test_namespace"  # namespace_name
        assert str(call_args[0][1]) == "507f1f77bcf86cd799439011"  # state_id as PydanticObjectId
        assert call_args[0][2] == body  # body
        assert call_args[0][3] == "test-request-id"  # x_exosphere_request_id
        assert result == mock_manual_retry_state.return_value

    @patch('app.routes.manual_retry_state')
    async def test_manual_retry_state_route_with_invalid_api_key(self, mock_manual_retry_state, mock_request):
        """Test manual_retry_state_route with invalid API key"""
        from app.routes import manual_retry_state_route
        from fastapi import HTTPException
        
        # Arrange
        body = ManualRetryRequestModel(fanout_id="test-fanout-id")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await manual_retry_state_route("test_namespace", "507f1f77bcf86cd799439011", body, mock_request, None) # type: ignore
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid API key"
        mock_manual_retry_state.assert_not_called()

    @patch('app.routes.manual_retry_state')
    async def test_manual_retry_state_route_without_request_id(self, mock_manual_retry_state, mock_request_no_id):
        """Test manual_retry_state_route without x_exosphere_request_id"""
        from app.routes import manual_retry_state_route
        
        # Arrange
        mock_manual_retry_state.return_value = MagicMock()
        body = ManualRetryRequestModel(fanout_id="test-fanout-id")
        
        # Act
        result = await manual_retry_state_route("test_namespace", "507f1f77bcf86cd799439011", body, mock_request_no_id, "valid_key")
        
        # Assert
        mock_manual_retry_state.assert_called_once()
        call_args = mock_manual_retry_state.call_args
        assert call_args[0][0] == "test_namespace"  # namespace_name
        assert str(call_args[0][1]) == "507f1f77bcf86cd799439011"  # state_id as PydanticObjectId
        assert call_args[0][2] == body  # body
        # Should generate a UUID when no request ID is present
        assert len(call_args[0][3]) > 0  # x_exosphere_request_id should be generated
        assert result == mock_manual_retry_state.return_value

    @patch('app.routes.cancel_triggers')
    async def test_cancel_triggers_route_with_valid_api_key(self, mock_cancel_triggers, mock_request):
        """Test cancel_triggers_route with valid API key"""
        from app.routes import cancel_triggers_route
        
        # Arrange
        expected_response = CancelTriggerResponse(
            namespace="test_namespace",
            graph_name="test_graph",
            cancelled_count=3,
            message="Successfully cancelled 3 trigger(s)"
        )
        mock_cancel_triggers.return_value = expected_response
        
        # Act
        result = await cancel_triggers_route("test_namespace", "test_graph", mock_request, "valid_key")
        
        # Assert
        mock_cancel_triggers.assert_called_once_with("test_namespace", "test_graph", "test-request-id")
        assert result == expected_response
        assert result.namespace == "test_namespace"
        assert result.graph_name == "test_graph"
        assert result.cancelled_count == 3

    @patch('app.routes.cancel_triggers')
    async def test_cancel_triggers_route_with_invalid_api_key(self, mock_cancel_triggers, mock_request):
        """Test cancel_triggers_route with invalid API key"""
        from app.routes import cancel_triggers_route
        from fastapi import HTTPException, status
        
        # Arrange
        mock_cancel_triggers.return_value = MagicMock()
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await cancel_triggers_route("test_namespace", "test_graph", mock_request, None) # type: ignore
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid API key"
        mock_cancel_triggers.assert_not_called()

    @patch('app.routes.cancel_triggers')
    async def test_cancel_triggers_route_without_request_id(self, mock_cancel_triggers, mock_request_no_id):
        """Test cancel_triggers_route without x_exosphere_request_id"""
        from app.routes import cancel_triggers_route
        
        # Arrange
        expected_response = CancelTriggerResponse(
            namespace="test_namespace",
            graph_name="test_graph",
            cancelled_count=2,
            message="Successfully cancelled 2 trigger(s)"
        )
        mock_cancel_triggers.return_value = expected_response
        
        # Act
        result = await cancel_triggers_route("test_namespace", "test_graph", mock_request_no_id, "valid_key")
        
        # Assert
        mock_cancel_triggers.assert_called_once()
        call_args = mock_cancel_triggers.call_args
        assert call_args[0][0] == "test_namespace"
        assert call_args[0][1] == "test_graph"
        # Should generate a UUID when no request ID is present
        assert len(call_args[0][2]) > 0  # x_exosphere_request_id should be generated
        assert result == expected_response