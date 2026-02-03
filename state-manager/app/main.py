"""
main file for exosphere state manager
"""
from beanie import init_beanie
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pymongo import AsyncMongoClient

# injecting singletons
from .singletons.logs_manager import LogsManager

# injecting middlewares
from .middlewares.unhandled_exceptions_middleware import (
    UnhandledExceptionsMiddleware,
)
from .middlewares.request_id_middleware import RequestIdMiddleware

# injecting models
from .models.db.state import State
from .models.db.graph_template_model import GraphTemplate
from .models.db.registered_node import RegisteredNode
from .models.db.store import Store
from .models.db.run import Run
from .models.db.trigger import DatabaseTriggers

# injecting routes
from .routes import router, global_router

# importing CORS config
from .config.cors import get_cors_config
from .config.settings import get_settings

# importing database health check function
from .utils.check_database_health import check_database_health

#scheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from .tasks.trigger_cron import trigger_cron
from .tasks.check_node_timeout import check_node_timeout

# init tasks
from .tasks.init_tasks import init_tasks
 
# Define models list
DOCUMENT_MODELS = [State, GraphTemplate, RegisteredNode, Store, Run, DatabaseTriggers]

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # begaining of the server
    logger = LogsManager().get_logger()
    logger.info("server starting")

    # Get settings
    settings = get_settings()

    # initializing beanie
    client = AsyncMongoClient(settings.mongo_uri)
    db = client[settings.mongo_database_name]
    await init_beanie(db, document_models=DOCUMENT_MODELS)
    logger.info("beanie dbs initialized")

    # performing init tasks
    await init_tasks()
    logger.info("init tasks completed")

    # initialize secret
    if not settings.state_manager_secret:
        raise ValueError("STATE_MANAGER_SECRET is not set")
    logger.info("secret initialized")

    # perform database health check
    await check_database_health(DOCUMENT_MODELS)

    scheduler.add_job(
        trigger_cron,
        CronTrigger.from_crontab("* * * * *"),
        replace_existing=True,
        misfire_grace_time=60,
        coalesce=True,
        max_instances=1,
        id="every_minute_task"
    )
    scheduler.add_job(
        check_node_timeout,
        CronTrigger.from_crontab("* * * * *"),
        replace_existing=True,
        misfire_grace_time=60,
        coalesce=True,
        max_instances=1,
        id="check_node_timeout_task"
    )
    scheduler.start()

    # main logic of the server
    yield

    # end of the server
    await client.close()
    scheduler.shutdown()
    logger.info("server stopped")


app = FastAPI(
    lifespan=lifespan,
    title="Exosphere State Manager",
    description="Exosphere State Manager",
    version="0.0.2-beta",
    contact={
        "name": "Nivedit Jain (Founder exosphere.host)",
        "email": "nivedit@exosphere.host",
    },
    license_info={
        "name": "Elastic License 2.0 (ELv2)",
        "url": "https://github.com/exospherehost/exosphere-api-server/blob/main/LICENSE",
    },
)

# Add middlewares in inner-to-outer order (last added runs first on request):  
# 1) UnhandledExceptions (inner)  
app.add_middleware(UnhandledExceptionsMiddleware)  
# 2) Request ID (middle)  
app.add_middleware(RequestIdMiddleware)  
# 3) CORS (outermost)  
app.add_middleware(CORSMiddleware, **get_cors_config())  


@app.get("/health")
def health() -> dict:
    return {"message": "OK"}

app.include_router(global_router)
app.include_router(router)