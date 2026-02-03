import base64
import time
import asyncio

from pymongo import IndexModel
from pydantic import Field, field_validator, PrivateAttr, model_validator
from typing import List, Self, Dict

from .base import BaseDatabaseModel
from ..graph_template_validation_status import GraphTemplateValidationStatus
from ..node_template_model import NodeTemplate
from app.utils.encrypter import get_encrypter
from app.models.dependent_string import DependentString
from app.models.retry_policy_model import RetryPolicyModel
from app.models.store_config_model import StoreConfig
from app.models.trigger_models import Trigger
from app.models.webhook_config_model import WebhookConfig

class GraphTemplate(BaseDatabaseModel):
    name: str = Field(..., description="Name of the graph")
    namespace: str = Field(..., description="Namespace of the graph")
    nodes: List[NodeTemplate] = Field(..., description="Nodes of the graph")
    validation_status: GraphTemplateValidationStatus = Field(..., description="Validation status of the graph")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors of the graph")
    secrets: Dict[str, str] = Field(default_factory=dict, description="Secrets of the graph")
    triggers: List[Trigger] = Field(default_factory=list, description="Triggers of the graph")
    retry_policy: RetryPolicyModel = Field(default_factory=RetryPolicyModel, description="Retry policy of the graph")
    store_config: StoreConfig = Field(default_factory=StoreConfig, description="Store config of the graph")
    webhook: WebhookConfig | None = Field(default=None, description="Optional webhook configuration for graph execution events")

    _node_by_identifier: Dict[str, NodeTemplate] | None = PrivateAttr(default=None)
    _parents_by_identifier: Dict[str, set[str]] | None = PrivateAttr(default=None) # type: ignore
    _root_node: NodeTemplate | None = PrivateAttr(default=None)
    _path_by_identifier: Dict[str, set[str]] | None = PrivateAttr(default=None) # type: ignore

    class Settings:
        validate_on_save = True
        indexes = [
            IndexModel(
                keys=[("name", 1), ("namespace", 1)],
                unique=True,
                name="unique_name_namespace"
            )
        ]

    def _build_node_by_identifier(self) -> None:
        self._node_by_identifier = {node.identifier: node for node in self.nodes}

    def _build_root_node(self) -> None:
        in_degree = {node.identifier: 0 for node in self.nodes}

        for node in self.nodes:
            if node.next_nodes is not None:
                for next_node in node.next_nodes:
                    in_degree[next_node] += 1

            if node.unites is not None:
                # If the node has a unit, it should have an in-degree of 1
                # As unites.node.identifier acts as the parent of the node
                in_degree[node.identifier] += 1
        
        zero_in_degree_nodes = [node for node in self.nodes if in_degree[node.identifier] == 0]
        if len(zero_in_degree_nodes) != 1:
            raise ValueError("There should be exactly one root node in the graph but found " + str(len(zero_in_degree_nodes)) + " nodes with zero in-degree: " + str(zero_in_degree_nodes))
        self._root_node = zero_in_degree_nodes[0]

    def _build_parents_path_by_identifier(self) -> None:
        try:
            root_node_identifier = self.get_root_node().identifier

            visited = {node.identifier: False for node in self.nodes}
            awaiting_parent: dict[str, list[str]] = {}

            self._parents_by_identifier: dict[str, set[str]] = {}
            self._path_by_identifier: dict[str, set[str]] = {}

            for node in self.nodes:
                self._parents_by_identifier[node.identifier] = set()
                self._path_by_identifier[node.identifier] = set()
                visited[node.identifier] = False

            def dfs(node_identifier: str, parents: set[str], path: set[str]) -> None:
                self._parents_by_identifier[node_identifier] = parents | self._parents_by_identifier[node_identifier]
                self._path_by_identifier[node_identifier] = path | self._path_by_identifier[node_identifier]

                if visited[node_identifier]:
                    return
                
                visited[node_identifier] = True

                node = self.get_node_by_identifier(node_identifier)

                assert node is not None

                if node.unites is None:
                    parents_for_children = parents | {node_identifier}
                elif visited[node.unites.identifier]:
                    parents = self._parents_by_identifier[node.unites.identifier]
                    self._parents_by_identifier[node.identifier] = parents | {node.unites.identifier}
                    parents_for_children = parents | {node.unites.identifier}
                else:
                    if node.unites.identifier not in awaiting_parent:
                        awaiting_parent[node.unites.identifier] = []
                    awaiting_parent[node.unites.identifier].append(node_identifier)
                    return
                
                if node_identifier in awaiting_parent:
                    for awaiting_identifier in awaiting_parent[node_identifier]:
                        dfs(awaiting_identifier, parents_for_children, self._path_by_identifier[awaiting_identifier])
                    del awaiting_parent[node_identifier]

                if node.next_nodes is None:
                    return

                for next_node_identifier in node.next_nodes:
                    dfs(next_node_identifier, parents_for_children, path | {node_identifier})

            dfs(root_node_identifier, set(), set())

            if len(awaiting_parent.keys()) > 0:
                raise ValueError(f"Graph is disconnected at: {awaiting_parent}")
    
        except Exception as e:
            raise ValueError(f"Error building dependency graph: {e}")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed_v = v.strip()
        if trimmed_v == "" or trimmed_v is None:
            raise ValueError("Name cannot be empty")
        return trimmed_v
    
    @field_validator('namespace')
    @classmethod
    def validate_namespace(cls, v: str) -> str:
        trimmed_v = v.strip()
        if trimmed_v == "" or trimmed_v is None:
            raise ValueError("Namespace cannot be empty")
        return trimmed_v

    @field_validator('secrets')
    @classmethod
    def validate_secrets(cls, v: Dict[str, str]) -> Dict[str, str]:
        for secret_name, secret_value in v.items():
            if not secret_name or not secret_value:
                raise ValueError("Secrets cannot be empty")
            cls._validate_secret_value(secret_value)
        return v
    
    @field_validator('nodes')
    @classmethod
    def validate_unique_identifiers(cls, v: List[NodeTemplate]) -> List[NodeTemplate]:
        identifiers = set()
        errors = []
        for node in v:
            if node.identifier in identifiers:
                errors.append(f"Node identifier {node.identifier} is not unique")
            identifiers.add(node.identifier)
        if errors:
            raise ValueError("\n".join(errors))
        return v
    
    @field_validator('nodes')
    @classmethod
    def validate_next_nodes_identifiers_exist(cls, v: List[NodeTemplate]) -> List[NodeTemplate]:
        identifiers = set()
        for node in v:
            identifiers.add(node.identifier)

        errors = []    
        for node in v:
            if node.next_nodes:
                for next_node in node.next_nodes:
                    if next_node not in identifiers:
                        errors.append(f"Node identifier {next_node} does not exist in the graph")
        if errors:
            raise ValueError("\n".join(errors))
        return v
    
    @classmethod
    def _validate_secret_value(cls, secret_value: str) -> None:
        # Check minimum length for AES-GCM encrypted string
        # 12 bytes nonce + minimum ciphertext + base64 encoding
        if len(secret_value) < 32:  # Minimum length for encrypted string
            raise ValueError("Value appears to be too short for an encrypted string")
               
        # Try to decode as base64 to ensure it's valid
        try:
            decoded = base64.urlsafe_b64decode(secret_value)
            if len(decoded) < 12:
                raise ValueError("Decoded value is too short to contain valid nonce")
        except Exception:
            raise ValueError("Value is not valid URL-safe base64 encoded")

    @model_validator(mode='after')
    def validate_unites_identifiers_exist(self) -> Self:
        errors = []
        identifiers = set()
        for node in self.nodes:
            identifiers.add(node.identifier)
        for node in self.nodes:
            if node.unites is not None:
                if node.unites.identifier not in identifiers:
                    errors.append(f"Node {node.identifier} has an unites target {node.unites.identifier} that does not exist")
                if node.unites.identifier == node.identifier:
                    errors.append(f"Node {node.identifier} has an unites target {node.unites.identifier} that is the same as the node itself")
        if errors:
            raise ValueError("\n".join(errors))
        return self

    @model_validator(mode='after')
    def validate_graph_is_connected(self) -> Self:
        errors = []
        root_node_identifier = self.get_root_node().identifier
        for node in self.nodes:
            if node.identifier == root_node_identifier:
                continue
            if root_node_identifier not in self.get_parents_by_identifier(node.identifier):
                errors.append(f"Node {node.identifier} is not connected to the root node")
        if errors:
            raise ValueError("\n".join(errors))
        return self
    
    @model_validator(mode='after')
    def validate_graph_is_acyclic(self) -> Self:
        errors = []
        for node in self.nodes:
            if node.identifier in self.get_path_by_identifier(node.identifier):
                errors.append(f"Node {node.identifier} is not acyclic")
        if errors:
            raise ValueError("\n".join(errors))
        return self
    
    @model_validator(mode='after')
    def verify_input_dependencies(self) -> Self:
        errors = []

        for node in self.nodes:
            for input_value in node.inputs.values():
                try:
                    if not isinstance(input_value, str):
                        errors.append(f"Input {input_value} is not a string")
                        continue

                    dependent_string = DependentString.create_dependent_string(input_value)
                    dependent_identifiers = set()
                    store_fields = set()

                    for key, field in dependent_string.get_identifier_field():
                        if key == "store":
                            store_fields.add(field)
                        else:
                            dependent_identifiers.add(key)

                    for identifier in dependent_identifiers:
                        if identifier not in self.get_parents_by_identifier(node.identifier):
                            errors.append(f"Input {input_value} depends on {identifier} but {identifier} is not a parent of {node.identifier}")

                    for field in store_fields:
                        if field not in self.store_config.required_keys and field not in self.store_config.default_values:
                            errors.append(f"Input {input_value} depends on {field} but {field} is not a required key or a default value")

                except Exception as e:
                    errors.append(f"Error creating dependent string for input {input_value} check syntax string: {str(e)}")
        if errors:
            raise ValueError("\n".join(errors))

        return self
        
    def set_secrets(self, secrets: Dict[str, str]) -> "GraphTemplate":
        self.secrets = {secret_name: get_encrypter().encrypt(secret_value) for secret_name, secret_value in secrets.items()}
        return self
    
    def get_secrets(self) -> Dict[str, str]:
        if not self.secrets:
            return {}
        return {secret_name: get_encrypter().decrypt(secret_value) for secret_name, secret_value in self.secrets.items()}
    
    def get_secret(self, secret_name: str) -> str | None:
        if not self.secrets:
            return None
        if secret_name not in self.secrets:
            return None
        return get_encrypter().decrypt(self.secrets[secret_name])

    def is_valid(self) -> bool:
        return self.validation_status == GraphTemplateValidationStatus.VALID

    def get_root_node(self) -> NodeTemplate:
        if self._root_node is None:
            self._build_root_node()
        assert self._root_node is not None
        return self._root_node

    def is_validating(self) -> bool:
        return self.validation_status in (GraphTemplateValidationStatus.ONGOING, GraphTemplateValidationStatus.PENDING)
    
    def get_node_by_identifier(self, identifier: str) -> NodeTemplate | None:
        """Get a node by its identifier using O(1) dictionary lookup."""
        if self._node_by_identifier is None:
            self._build_node_by_identifier()

        assert self._node_by_identifier is not None
        return self._node_by_identifier.get(identifier)
    
    def get_parents_by_identifier(self, identifier: str) -> set[str]:
        if self._parents_by_identifier is None:
            self._build_parents_path_by_identifier()
        
        assert self._parents_by_identifier is not None
        return self._parents_by_identifier.get(identifier, set())
    
    def get_path_by_identifier(self, identifier: str) -> set[str]:
        if self._path_by_identifier is None:
            self._build_parents_path_by_identifier()
        
        assert self._path_by_identifier is not None
        return self._path_by_identifier.get(identifier, set())
    
    @staticmethod
    async def get(namespace: str, graph_name: str) -> "GraphTemplate":
        graph_template = await GraphTemplate.find_one(GraphTemplate.namespace == namespace,GraphTemplate.name == graph_name)
        if not graph_template:
            raise ValueError(f"Graph template not found for namespace: {namespace} and graph name: {graph_name}")
        return graph_template
    
    @staticmethod
    async def get_valid(namespace: str, graph_name: str, polling_interval: float = 1.0, timeout: float = 300.0) -> "GraphTemplate":
        # Validate polling_interval and timeout
        if polling_interval <= 0:
            raise ValueError("polling_interval must be positive")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        
        # Coerce polling_interval to a sensible minimum
        if polling_interval < 0.1:
            polling_interval = 0.1
        
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            graph_template = await GraphTemplate.get(namespace, graph_name)
            if graph_template.is_valid():
                return graph_template
            if graph_template.is_validating():
                await asyncio.sleep(polling_interval)
            else:
                raise ValueError(f"Graph template is in a non-validating state: {graph_template.validation_status.value} for namespace: {namespace} and graph name: {graph_name}")
        raise ValueError(f"Graph template is not valid for namespace: {namespace} and graph name: {graph_name} after {timeout} seconds")
