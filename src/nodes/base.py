from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from context import RuntimeContext

class NodeHandler(ABC):
    """
    Base class for all Node Handlers.
    每個節點類型 (Click, Wait, etc.) 都應該繼承此類別。
    """
    
    @property
    @abstractmethod
    def node_type(self) -> str:
        """The string identifier for this node type (e.g. 'click', 'wait')"""
        pass

    @abstractmethod
    def execute(self, node: Dict[str, Any], context: RuntimeContext) -> Optional[str]:
        """
        Execute the node logic.
        
        Args:
            node: The node dictionary (properties, inputs, connections).
            context: The current runtime state.
            
        Returns:
            Optional[str]: The ID of the NEXT node to execute. 
                           Returns None if execution should stop or flow ends.
        """
        pass

    def get_input_value(self, node: Dict[str, Any], input_name: str, default_val: Any, context: RuntimeContext) -> Any:
        """Helper to resolve input links (Data Flow)"""
        links = node.get('input_links', {})
        if input_name in links:
            link = links[input_name]
            # link = { 'id': source_node_id, 'slot': source_slot_index }
            res = context.get_output(link['id'], link['slot'])
            if res is not None:
                return res
        return default_val
