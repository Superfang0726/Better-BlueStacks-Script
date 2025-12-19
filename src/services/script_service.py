import os
import json
from typing import List, Dict, Any, Optional
from shared import log_message

class ScriptService:
    SCRIPTS_DIR = 'scripts'

    @staticmethod
    def load_and_normalize(script_name: str) -> List[Dict[str, Any]]:
        """
        Load a script by name, normalize it from various stored formats 
        (Raw LiteGraph, stringified JSON, etc.) into a linear list of Engine Nodes.
        """
        script_path = os.path.join(ScriptService.SCRIPTS_DIR, f"{script_name}.json")
        if not os.path.exists(script_path):
            log_message(f"Error: Script file '{script_name}' not found.")
            return []

        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                script_data = json.load(f)

            # Handle Double-JSON encoding (fix from previous sessions)
            if isinstance(script_data, str):
                try:
                    script_data = json.loads(script_data)
                except Exception as e:
                    log_message(f"Error parsing script JSON string: {e}")
                    return []

            return ScriptService.normalize(script_data)
        except Exception as e:
            log_message(f"Error loading script {script_name}: {e}")
            return []

    @staticmethod
    def normalize(data: Any) -> List[Dict[str, Any]]:
        """
        Convert any accepted input format into a list of Node objects with 'next' pointers.
        """
        # Case 1: Raw LiteGraph Export (serialized graph)
        if isinstance(data, dict) and 'nodes' in data and 'links' in data:
            return ScriptService._convert_litegraph(data)
        
        # Case 2: Already processed 'actions' list (Legacy or internal)
        if isinstance(data, dict) and 'actions' in data:
            return data['actions']
        
        # Case 3: List of nodes/actions
        if isinstance(data, list):
            return data
            
        # Case 4: LiteGraph export but wrapped in 'content'? (routes.py behavior)
        # routes.py saves { name:..., content: ... }
        # But load_and_normalize usually reads the FILE content which IS the saved content.
        # So we likely hit Case 1 or Case 2.
        
        return []

    @staticmethod
    def _convert_litegraph(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        nodes = data.get('nodes', [])
        links = data.get('links', [])
        
        # Map links: origin_id -> { slot_index: target_node_id }
        connections = {} 
        link_map = { l[0]: l for l in links } # link_id -> link_data
        
        for link in links:
            # [id, origin_id, origin_slot, target_id, target_slot, type]
            if len(link) >= 6:
                origin_id = link[1]
                origin_slot = link[2]
                target_id = link[3]
                if origin_id not in connections: connections[origin_id] = {}
                connections[origin_id][origin_slot] = target_id
                
        normalized_nodes = []
        for node in nodes:
            # Strip 'bot/' prefix
            node_type = node['type'].replace('bot/', '')
            
            new_node = {
                'id': node['id'],
                'type': node_type,
                'properties': node.get('properties', {}),
                'input_links': {}
            }
            
            # Outputs (Next Pointers)
            conns = connections.get(node['id'], {})
            
            # Heuristic mapping based on common node types
            # Ideally this schema should be defined in NodeHandler, 
            # but decoupling parsing from execution is good.
            if node_type == 'loop':
                new_node['next_body'] = conns.get(str(0)) or conns.get(0)
                new_node['next_exit'] = conns.get(str(1)) or conns.get(1)
            elif node_type in ['find_image', 'check_pixel']:
                # Support both int and string keys for robustness
                # Try slot 0 (Found) and slot 1 (Not Found)
                new_node['next_found'] = conns.get(0) or conns.get(str(0))
                new_node['next_not_found'] = conns.get(1) or conns.get(str(1))
                # If these are missing, fallback to whatever is in slot 0/1 anyway
                if new_node['next_found'] is None: new_node['next_found'] = conns.get(0)
                if new_node['next_not_found'] is None: new_node['next_not_found'] = conns.get(1)
                
                # Default/Fallthrough to index 0 if only one connection exists anywhere? 
                # No, LiteGraph users expect explicit branching.
            else:
                # Default linear
                new_node['next'] = conns.get(0) or conns.get(str(0))
                
            # Inputs (Data Flow)
            if 'inputs' in node:
                for inp in node['inputs']:
                    link_id = inp.get('link')
                    if link_id and link_id in link_map:
                        l = link_map[link_id]
                        new_node['input_links'][inp['name']] = { 'id': l[1], 'slot': l[2] }
                        
            normalized_nodes.append(new_node)
            
        return normalized_nodes
