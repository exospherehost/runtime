import pytest
from pydantic import ValidationError
from app.models.trigger_models import CronTrigger, Trigger, TriggerTypeEnum


class TestCronTrigger:
    """Test cases for CronTrigger model"""

    def test_valid_cron_trigger_with_timezone(self):
        """Test creating a valid cron trigger with timezone"""
        trigger = CronTrigger(expression="0 9 * * *", timezone="America/New_York")
        assert trigger.expression == "0 9 * * *"
        assert trigger.timezone == "America/New_York"

    def test_valid_cron_trigger_without_timezone(self):
        """Test creating a valid cron trigger without timezone defaults to UTC"""
        trigger = CronTrigger(expression="0 9 * * *")
        assert trigger.expression == "0 9 * * *"
        assert trigger.timezone == "UTC"

    def test_valid_cron_trigger_with_utc_timezone(self):
        """Test creating a valid cron trigger with UTC timezone"""
        trigger = CronTrigger(expression="0 9 * * *", timezone="UTC")
        assert trigger.expression == "0 9 * * *"
        assert trigger.timezone == "UTC"

    def test_valid_cron_trigger_with_europe_london(self):
        """Test creating a valid cron trigger with Europe/London timezone"""
        trigger = CronTrigger(expression="0 17 * * *", timezone="Europe/London")
        assert trigger.expression == "0 17 * * *"
        assert trigger.timezone == "Europe/London"

    def test_valid_cron_trigger_with_asia_tokyo(self):
        """Test creating a valid cron trigger with Asia/Tokyo timezone"""
        trigger = CronTrigger(expression="30 8 * * 1-5", timezone="Asia/Tokyo")
        assert trigger.expression == "30 8 * * 1-5"
        assert trigger.timezone == "Asia/Tokyo"

    def test_invalid_cron_expression(self):
        """Test creating a cron trigger with invalid expression"""
        with pytest.raises(ValidationError) as exc_info:
            CronTrigger(expression="invalid cron", timezone="UTC")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        # Check the error message (Pydantic v2 doesn't always populate ctx)
        error_msg = errors[0].get("msg") or str(errors[0])
        assert "Invalid cron expression" in error_msg

    def test_invalid_timezone(self):
        """Test creating a cron trigger with invalid timezone"""
        with pytest.raises(ValidationError) as exc_info:
            CronTrigger(expression="0 9 * * *", timezone="Invalid/Timezone")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        # Check the error message (Pydantic v2 doesn't always populate ctx)
        error_msg = errors[0].get("msg") or str(errors[0])
        assert "Invalid timezone" in error_msg
        assert "Invalid/Timezone" in error_msg

    def test_complex_cron_expression_with_timezone(self):
        """Test complex cron expression with timezone"""
        trigger = CronTrigger(expression="0 0 1,15 * *", timezone="America/Los_Angeles")
        assert trigger.expression == "0 0 1,15 * *"
        assert trigger.timezone == "America/Los_Angeles"

    def test_every_15_minutes_cron_with_timezone(self):
        """Test every 15 minutes cron with timezone"""
        trigger = CronTrigger(expression="*/15 * * * *", timezone="Europe/Paris")
        assert trigger.expression == "*/15 * * * *"
        assert trigger.timezone == "Europe/Paris"


class TestTrigger:
    """Test cases for Trigger model"""

    def test_valid_trigger_with_cron_and_timezone(self):
        """Test creating a valid trigger with CRON type and timezone"""
        trigger = Trigger(
            value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "America/New_York"}
        )
        assert trigger.value.type == TriggerTypeEnum.CRON
        assert trigger.value.expression == "0 9 * * *"
        assert trigger.value.timezone == "America/New_York"

    def test_valid_trigger_with_cron_without_timezone(self):
        """Test creating a valid trigger with CRON type without timezone"""
        trigger = Trigger(
            value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *"}
        )
        assert trigger.value.type == TriggerTypeEnum.CRON
        assert trigger.value.expression == "0 9 * * *"
        assert trigger.value.timezone == "UTC"  # Should default to UTC

    def test_invalid_trigger_with_invalid_cron_expression(self):
        """Test creating a trigger with invalid cron expression"""
        with pytest.raises(ValidationError) as exc_info:
            Trigger(
                value={"type": TriggerTypeEnum.CRON, "expression": "invalid cron"}
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_invalid_trigger_with_invalid_timezone(self):
        """Test creating a trigger with invalid timezone"""
        with pytest.raises(ValidationError) as exc_info:
            Trigger(
                value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "Invalid/Zone"}
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_trigger_model_equality_with_identical_values(self):
        """Test Pydantic model equality for triggers with identical values.

        Note: This test verifies model-level equality only, not deduplication logic.
        The actual deduplication of triggers is handled in verify_graph.py's create_crons function.
        """
        # Create first trigger
        trigger1 = Trigger(
            value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "America/New_York"}
        )

        # Create second trigger with identical values
        trigger2 = Trigger(
            value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "America/New_York"}
        )

        # Both triggers should be created successfully
        assert trigger1.value.type == TriggerTypeEnum.CRON
        assert trigger2.value.type == TriggerTypeEnum.CRON
        assert trigger1.value.expression == "0 9 * * *"
        assert trigger2.value.expression == "0 9 * * *"
        assert trigger1.value.timezone == "America/New_York"
        assert trigger2.value.timezone == "America/New_York"

        # Test equality - Pydantic models with same values should be equal
        assert trigger1 == trigger2

        # Test that they are different objects in memory
        assert trigger1 is not trigger2

        # Test model_dump produces identical output
        assert trigger1.model_dump() == trigger2.model_dump()

    def test_duplicate_triggers_different_timezones(self):
        """Test creating two triggers with same expression but different timezones"""
        trigger1 = Trigger(
            value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "America/New_York"}
        )

        trigger2 = Trigger(
            value={"type": TriggerTypeEnum.CRON, "expression": "0 9 * * *", "timezone": "Europe/London"}
        )

        # Both triggers should be created successfully
        assert trigger1.value.type == TriggerTypeEnum.CRON
        assert trigger2.value.type == TriggerTypeEnum.CRON

        # They should NOT be equal due to different timezones
        assert trigger1 != trigger2

        # Verify the difference is in timezone
        assert trigger1.value.timezone == "America/New_York"
        assert trigger2.value.timezone == "Europe/London"