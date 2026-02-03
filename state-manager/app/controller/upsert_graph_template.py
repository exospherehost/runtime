from datetime import datetime, timedelta, timezone

from app.singletons.logs_manager import LogsManager
from app.models.graph_models import UpsertGraphTemplateRequest, UpsertGraphTemplateResponse
from app.models.db.graph_template_model import GraphTemplate
from app.models.graph_template_validation_status import GraphTemplateValidationStatus
from app.tasks.verify_graph import verify_graph
from app.models.db.trigger import DatabaseTriggers
from app.models.trigger_models import TriggerStatusEnum, TriggerTypeEnum
from app.config.settings import get_settings

from fastapi import BackgroundTasks, HTTPException

logger = LogsManager().get_logger()


async def upsert_graph_template(
    namespace_name: str,
    graph_name: str,
    body: UpsertGraphTemplateRequest,
    x_exosphere_request_id: str,
    background_tasks: BackgroundTasks,
) -> UpsertGraphTemplateResponse:
    try:
        # Load settings at request time so runtime config changes are picked up
        settings = get_settings()
        old_triggers = []

        graph_template = await GraphTemplate.find_one(
            GraphTemplate.name == graph_name,
            GraphTemplate.namespace == namespace_name,
        )

        try:
            if graph_template:
                logger.info(
                    "Graph template already exists in namespace",
                    graph_template=graph_template,
                    namespace_name=namespace_name,
                    x_exosphere_request_id=x_exosphere_request_id,
                )
                old_triggers = graph_template.triggers

                graph_template.set_secrets(body.secrets)
                graph_template.validation_status = GraphTemplateValidationStatus.PENDING
                graph_template.validation_errors = []
                graph_template.retry_policy = body.retry_policy
                graph_template.store_config = body.store_config
                graph_template.nodes = body.nodes
                graph_template.triggers = body.triggers
                await graph_template.save()

            else:
                logger.info(
                    "Graph template does not exist in namespace",
                    namespace_name=namespace_name,
                    graph_name=graph_name,
                    x_exosphere_request_id=x_exosphere_request_id,
                )

                graph_template = await GraphTemplate.insert(
                    GraphTemplate(
                        name=graph_name,
                        namespace=namespace_name,
                        nodes=body.nodes,
                        validation_status=GraphTemplateValidationStatus.PENDING,
                        validation_errors=[],
                        retry_policy=body.retry_policy,
                        store_config=body.store_config,
                        triggers=body.triggers,
                    ).set_secrets(body.secrets)
                )
        except ValueError as e:
            logger.error(
                "Error validating graph template",
                error=e,
                x_exosphere_request_id=x_exosphere_request_id,
            )
            raise HTTPException(
                status_code=400,
                detail=f"Error validating graph template: {str(e)}",
            )

        # Previously:
        # await DatabaseTriggers.find(...).delete_many()
        #
        # Now: bulk update to mark matching CRON triggers as CANCELLED
        # and set expires_at so TTL can clean them up later.
        if len(old_triggers) > 0:
            cron_expressions = [
                trigger.value["expression"]
                for trigger in old_triggers
                if trigger.type == TriggerTypeEnum.CRON
            ]

            if cron_expressions:
                expires_at = datetime.now(timezone.utc) + timedelta(
                    hours=settings.trigger_retention_hours
                )

                await DatabaseTriggers.get_pymongo_collection().update_many(
                    {
                        "graph_name": graph_name,
                        "namespace": namespace_name,  # ensure we only affect this namespace
                        "trigger_status": TriggerStatusEnum.PENDING.value,
                        "type": TriggerTypeEnum.CRON.value,
                        "expression": {"$in": cron_expressions},
                    },
                    {
                        "$set": {
                            "trigger_status": TriggerStatusEnum.CANCELLED.value,
                            "expires_at": expires_at,
                        }
                    },
                )

        background_tasks.add_task(verify_graph, graph_template)

        return UpsertGraphTemplateResponse(
            nodes=graph_template.nodes,
            validation_status=graph_template.validation_status,
            validation_errors=graph_template.validation_errors,
            secrets={
                secret_name: True
                for secret_name in graph_template.get_secrets().keys()
            },
            retry_policy=graph_template.retry_policy,
            store_config=graph_template.store_config,
            triggers=graph_template.triggers,
            created_at=graph_template.created_at,
            updated_at=graph_template.updated_at,
        )

    except Exception as e:
        logger.error(
            "Error upserting graph template",
            error=e,
            x_exosphere_request_id=x_exosphere_request_id,
        )
        # re-raise with original traceback preserved
        raise
