"""
Integration tests for trigger deduplication logic in create_crons.
These tests verify that duplicate triggers with identical expression and timezone
result in only one DatabaseTriggers row being created.
"""
import pytest
from typing import List, Optional, Set, Tuple

from app.models.db.graph_template_model import GraphTemplate
from app.models.graph_template_validation_status import GraphTemplateValidationStatus
from app.models.node_template_model import NodeTemplate
from app.models.trigger_models import Trigger, TriggerTypeEnum
from app.models.db.trigger import DatabaseTriggers
from app.tasks.verify_graph import create_crons


async def run_deduplication_test(
    graph_name: str,
    triggers: List[Trigger],
    expected_count: int,
    expected_pairs: Optional[Set[Tuple[str, str]]] = None
):
    """Helper to test trigger deduplication with actual database.

    Args:
        graph_name: Unique name for the test graph
        triggers: List of Trigger objects to create
        expected_count: Expected number of unique triggers in database
        expected_pairs: Optional set of (expression, timezone) tuples to verify
    """
    namespace = "test_namespace"

    # Pre-test cleanup
    await DatabaseTriggers.find(
        DatabaseTriggers.graph_name == graph_name,
        DatabaseTriggers.namespace == namespace
    ).delete_many()

    # Create graph template with triggers
    graph_template = GraphTemplate(
        name=graph_name,
        namespace=namespace,
        nodes=[
            NodeTemplate(
                node_name="test_node",
                namespace=namespace,
                identifier="test_node",
                inputs={},
                next_nodes=None,
                unites=None
            )
        ],
        validation_status=GraphTemplateValidationStatus.PENDING,
        triggers=triggers
    )

    # Call create_crons
    await create_crons(graph_template)

    # Query database
    triggers_in_db = await DatabaseTriggers.find(
        DatabaseTriggers.graph_name == graph_name,
        DatabaseTriggers.namespace == namespace
    ).to_list()

    # Assert count
    assert len(triggers_in_db) == expected_count

    # Assert pairs if provided
    if expected_pairs is not None:
        actual_pairs = {(t.expression, t.timezone) for t in triggers_in_db}
        assert actual_pairs == expected_pairs

    # Post-test cleanup
    await DatabaseTriggers.find(
        DatabaseTriggers.graph_name == graph_name,
        DatabaseTriggers.namespace == namespace
    ).delete_many()


@pytest.mark.asyncio(loop_scope="session")
async def test_create_crons_deduplicates_identical_triggers(app_started):
    """Test that create_crons deduplicates triggers with identical expression and timezone

    This integration test verifies the actual database behavior, not mocks.
    It creates a GraphTemplate with duplicate CRON triggers and verifies that only
    one DatabaseTriggers row exists per (expression, timezone) pair.
    """
    await run_deduplication_test(
        graph_name="test_dedup_graph",
        triggers=[
            Trigger(value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "America/New_York"}),
            Trigger(value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "America/New_York"}),
            Trigger(value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "America/New_York"}),
        ],
        expected_count=1,
        expected_pairs={("0 9 * * *", "America/New_York")}
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_create_crons_keeps_triggers_with_different_timezones(app_started):
    """Test that create_crons keeps triggers with same expression but different timezones

    This verifies that triggers are only deduplicated when BOTH expression AND timezone match.
    """
    await run_deduplication_test(
        graph_name="test_timezone_graph",
        triggers=[
            Trigger(value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "America/New_York"}),
            Trigger(value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "Europe/London"}),
            Trigger(value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "Asia/Tokyo"}),
        ],
        expected_count=3,
        expected_pairs={
            ("0 9 * * *", "America/New_York"),
            ("0 9 * * *", "Europe/London"),
            ("0 9 * * *", "Asia/Tokyo")
        }
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_create_crons_keeps_triggers_with_different_expressions(app_started):
    """Test that create_crons keeps triggers with different expressions

    This verifies basic functionality - triggers with different expressions should all be created.
    """
    await run_deduplication_test(
        graph_name="test_expr_graph",
        triggers=[
            Trigger(value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "UTC"}),
            Trigger(value={"type": TriggerTypeEnum.CRON, "expression": "0 12 * * *", "timezone": "UTC"}),
            Trigger(value={"type": TriggerTypeEnum.CRON, "expression": "*/15 * * * *", "timezone": "UTC"}),
        ],
        expected_count=3,
        expected_pairs={
            ("0 9 * * *", "UTC"),
            ("0 12 * * *", "UTC"),
            ("*/15 * * * *", "UTC")
        }
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_create_crons_complex_deduplication_scenario(app_started):
    """Test complex deduplication scenario with mix of duplicates and unique triggers

    This tests a realistic scenario where a graph template has:
    - Some duplicate triggers (same expression + timezone)
    - Some unique triggers
    - Triggers with same expression but different timezone
    """
    await run_deduplication_test(
        graph_name="test_complex_graph",
        triggers=[
            # Three duplicates - should result in 1 DB row
            Trigger(value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "America/New_York"}),
            Trigger(value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "America/New_York"}),
            Trigger(value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "America/New_York"}),
            # Same expression, different timezone - should result in 1 DB row
            Trigger(value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "Europe/London"}),
            # Two duplicates of a different expression - should result in 1 DB row
            Trigger(value={"type": TriggerTypeEnum.CRON, "expression": "*/15 * * * *", "timezone": "UTC"}),
            Trigger(value={"type": TriggerTypeEnum.CRON, "expression": "*/15 * * * *", "timezone": "UTC"}),
            # Unique trigger - should result in 1 DB row
            Trigger(value={"type": TriggerTypeEnum.CRON, "expression": "0 0 1 * *", "timezone": "Asia/Tokyo"}),
        ],
        expected_count=4,
        expected_pairs={
            ("0 9 * * *", "America/New_York"),
            ("0 9 * * *", "Europe/London"),
            ("*/15 * * * *", "UTC"),
            ("0 0 1 * *", "Asia/Tokyo"),
        }
    )