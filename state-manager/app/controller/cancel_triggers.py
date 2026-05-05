"""
Controller for cancelling pending triggers for a graph
"""
import asyncio
from app.models.cancel_trigger_models import CancelTriggerResponse
from app.models.db.trigger import DatabaseTriggers
from app.models.trigger_models import TriggerStatusEnum
from app.singletons.logs_manager import LogsManager
from app.config.settings import get_settings
from app.tasks.trigger_cron import mark_as_cancelled
from beanie.operators import In

logger = LogsManager().get_logger()

async def cancel_triggers(namespace_name: str, graph_name: str, x_exosphere_request_id: str) -> CancelTriggerResponse:
    """
    Cancel all pending or triggering triggers for a specific graph
    
    Args:
        namespace_name: The namespace of the graph
        graph_name: The name of the graph
        x_exosphere_request_id: Request ID for logging
        
    Returns:
        CancelTriggerResponse with cancellation details
    """
    try:
        logger.info(f"Request to cancel triggers for graph {graph_name} in namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        
        # Find all PENDING or TRIGGERING triggers for this graph
        triggers = await DatabaseTriggers.find(
            DatabaseTriggers.namespace == namespace_name,
            DatabaseTriggers.graph_name == graph_name,
            In(DatabaseTriggers.trigger_status, [TriggerStatusEnum.PENDING, TriggerStatusEnum.TRIGGERING])
        ).to_list()
        
        if not triggers:
            logger.info(f"No pending triggers found for graph {graph_name} in namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
            return CancelTriggerResponse(
                namespace=namespace_name,
                graph_name=graph_name,
                cancelled_count=0,
                message="No pending triggers found to cancel"
            )
        
        # Get retention hours from settings
        settings = get_settings()
        retention_hours = settings.trigger_retention_hours
        
        # Cancel each trigger concurrently
        cancelled_count = len(triggers)
        cancellation_tasks = [mark_as_cancelled(trigger, retention_hours) for trigger in triggers]
        await asyncio.gather(*cancellation_tasks)
        
        logger.info(f"Cancelled {cancelled_count} triggers for graph {graph_name} in namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        
        return CancelTriggerResponse(
            namespace=namespace_name,
            graph_name=graph_name,
            cancelled_count=cancelled_count,
            message=f"Successfully cancelled {cancelled_count} trigger(s)"
        )
        
    except Exception as e:
        logger.error(f"Error cancelling triggers for graph {graph_name} in namespace {namespace_name}: {str(e)}", x_exosphere_request_id=x_exosphere_request_id)
        raise

