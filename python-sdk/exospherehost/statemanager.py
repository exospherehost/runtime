import os
import aiohttp
import asyncio
import time

from .models import GraphNodeModel, RetryPolicyModel, StoreConfigModel, CronTrigger


class StateManager:

    def __init__(self, namespace: str, state_manager_uri: str | None = None, key: str | None = None, state_manager_version: str = "v0"):
        self._state_manager_uri = state_manager_uri
        self._key = key
        self._state_manager_version = state_manager_version
        self._namespace = namespace

        self._set_config_from_env()

    def _set_config_from_env(self):
        """
        Set configuration from environment variables if not provided.
        """
        if self._state_manager_uri is None:
            self._state_manager_uri = os.environ.get("EXOSPHERE_STATE_MANAGER_URI")
        if self._key is None:
            self._key = os.environ.get("EXOSPHERE_API_KEY")

    def _get_trigger_state_endpoint(self, graph_name: str):
        return f"{self._state_manager_uri}/{self._state_manager_version}/namespace/{self._namespace}/graph/{graph_name}/trigger"
    
    def _get_upsert_graph_endpoint(self, graph_name: str):
        return f"{self._state_manager_uri}/{self._state_manager_version}/namespace/{self._namespace}/graph/{graph_name}"
    
    def _get_get_graph_endpoint(self, graph_name: str):
        return f"{self._state_manager_uri}/{self._state_manager_version}/namespace/{self._namespace}/graph/{graph_name}"

    async def trigger(self, graph_name: str, inputs: dict[str, str] | None = None, store: dict[str, str] | None = None, start_delay: int = 0):
        """
        Trigger execution of a graph.
        
        Beta: This method now supports an optional **store** parameter that lets you
        pass a key-value map that is persisted for the lifetime of the graph run. All
        keys **and** values must be strings in the current beta release – the schema
        may change in future versions.
        
        Args:
            graph_name (str): Name of the graph you want to run.
            inputs (dict[str, str] | None): Optional inputs for the first node in the
                graph. Strings only.
            store (dict[str, str] | None): Optional key-value store that will be merged
                into the graph-level store before execution (beta).
            start_delay (int): Optional delay in milliseconds before the graph starts execution.

        Returns:
            dict: JSON payload returned by the state-manager API.
        
        Raises:
            Exception: If the request fails.
        
        Example:
            ```python
            # Trigger with inputs only
            await state_manager.trigger("my-graph", inputs={"user_id": "123"})

            # Trigger with inputs **and** a beta store
            await state_manager.trigger(
                "my-graph",
                inputs={"user_id": "123"},
                store={"cursor": "0"}  # beta
            )
            ```
        """
        if inputs is None: 
            inputs = {}
        if store is None:
            store = {}
        
        body = {
            "start_delay": start_delay,
            "inputs": inputs,
            "store": store
        }
        headers = {
            "x-api-key": self._key
        }
        endpoint = self._get_trigger_state_endpoint(graph_name)
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=body, headers=headers) as response: # type: ignore
                if response.status != 200:
                    raise Exception(f"Failed to trigger state: {response.status} {await response.text()}")
                return await response.json()
            
    async def get_graph(self, graph_name: str):
        """
        Retrieve information about a specific graph from the state manager.
        
        This method fetches the current state and configuration of a graph,
        including its validation status, nodes, and any validation errors.
        
        Args:
            graph_name (str): The name of the graph to retrieve.
            
        Returns:
            dict: The JSON response from the state manager API containing the
                graph information, including validation status, nodes, and errors.
                
        Raises:
            Exception: If the API request fails with a non-200 status code. The exception
                message includes the HTTP status code and response text for debugging.
                
        Example:
            ```python
            # Get information about a specific graph
            graph_info = await state_manager.get_graph("my-workflow-graph")
            print(f"Graph status: {graph_info['validation_status']}")
            ```
        """
        endpoint = self._get_get_graph_endpoint(graph_name)
        headers = {
            "x-api-key": self._key
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, headers=headers) as response: # type: ignore
                if response.status != 200:
                    raise Exception(f"Failed to get graph: {response.status} {await response.text()}")
                return await response.json()

    async def upsert_graph(self, graph_name: str, graph_nodes: list[GraphNodeModel], secrets: dict[str, str], retry_policy: RetryPolicyModel | None = None, store_config: StoreConfigModel | None = None, triggers: list[CronTrigger] | None = None, validation_timeout: int = 60, polling_interval: int = 1):
        """
        Create or update a graph definition.

        Beta: `store_config` is a new field that allows you to configure a
        namespaced key-value store that lives for the duration of a graph run. The
        feature is in beta and the shape of `store_config` may change.
        
        After submitting the graph, this helper polls the state-manager until the
        graph has been validated (or the timeout is hit).
        
        Args:
            graph_name (str): Graph identifier.
            graph_nodes (list[GraphNodeModel]): List of graph node models defining the workflow.
            secrets (dict[str, str]): Secrets available to all nodes.
            retry_policy (RetryPolicyModel | None): Optional per-node retry policy configuration.
            store_config (StoreConfigModel | None): Beta configuration for the
                graph-level store (schema is subject to change).
            triggers (list[CronTrigger] | None): Optional list of cron triggers for automatic
                graph execution. Each trigger contains a cron expression that schedules when
                the graph should be executed automatically.
            validation_timeout (int): Seconds to wait for validation (default 60).
            polling_interval (int): Polling interval in seconds (default 1).
        
        Returns:
            dict: Validated graph object returned by the API.
        
        Raises:
            Exception: If validation fails or times out.
        """
        endpoint = self._get_upsert_graph_endpoint(graph_name)
        headers = {
            "x-api-key": self._key
        }
        body = {
            "secrets": secrets,
            "nodes": [node.model_dump() for node in graph_nodes]
        }

        if retry_policy is not None:
            body["retry_policy"] = retry_policy.model_dump()
        if store_config is not None:
            body["store_config"] = store_config.model_dump()
        if triggers is not None:
            body["triggers"] = [
                {
                    "value": {
                        "type": "CRON",
                        "expression": trigger.expression,
                        "timezone": trigger.timezone
                    }
                }
                for trigger in triggers
            ]

        async with aiohttp.ClientSession() as session:
            async with session.put(endpoint, json=body, headers=headers) as response: # type: ignore
                if response.status not in [200, 201]:
                    raise Exception(f"Failed to upsert graph: {response.status} {await response.text()}")
                graph = await response.json()

        validation_state = graph["validation_status"]
        
        start_time = time.monotonic()
        while validation_state == "PENDING":
            if time.monotonic() - start_time > validation_timeout:
                raise Exception(f"Graph validation check timed out after {validation_timeout} seconds")
            await asyncio.sleep(polling_interval)
            graph = await self.get_graph(graph_name)
            validation_state = graph["validation_status"]
        
        if validation_state != "VALID":
            raise Exception(f"Graph validation failed: {graph['validation_status']} and errors: {graph['validation_errors']}")

        return graph