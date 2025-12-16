import time
from typing import Dict, Any, Optional
from context import RuntimeContext
from nodes.base import NodeHandler
from shared import log_message

class StartNode(NodeHandler):
    @property
    def node_type(self): return "start"
    
    def execute(self, node: Dict[str, Any], context: RuntimeContext) -> Optional[str]:
        # Start node just moves to next
        return node.get('next')

class ClickNode(NodeHandler):
    @property
    def node_type(self): return "click"
    
    def execute(self, node: Dict[str, Any], context: RuntimeContext) -> Optional[str]:
        props = node.get('properties', {})
        x = int(self.get_input_value(node, 'X', props.get('x', 500), context))
        y = int(self.get_input_value(node, 'Y', props.get('y', 500), context))
        
        context.bot.click(x, y)
        return node.get('next')

class SwipeNode(NodeHandler):
    @property
    def node_type(self): return "swipe"
    
    def execute(self, node: Dict[str, Any], context: RuntimeContext) -> Optional[str]:
        props = node.get('properties', {})
        x1 = int(self.get_input_value(node, 'X1', props.get('x1', 500), context))
        y1 = int(self.get_input_value(node, 'Y1', props.get('y1', 800), context))
        x2 = int(self.get_input_value(node, 'X2', props.get('x2', 500), context))
        y2 = int(self.get_input_value(node, 'Y2', props.get('y2', 200), context))
        dur = int(props.get('duration', 500))
        
        context.bot.swipe(x1, y1, x2, y2, dur)
        return node.get('next')

class WaitNode(NodeHandler):
    @property
    def node_type(self): return "wait"
    
    def execute(self, node: Dict[str, Any], context: RuntimeContext) -> Optional[str]:
        props = node.get('properties', {})
        sec = float(props.get('seconds', 1.0))
        log_message(f"Waiting {sec}s...")
        time.sleep(sec)
        return node.get('next')
