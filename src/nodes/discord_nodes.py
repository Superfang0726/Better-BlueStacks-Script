import os
import asyncio
import discord
import threading
from typing import Dict, Any, Optional
from context import RuntimeContext
from nodes.base import NodeHandler
from shared import log_message
from settings import load_settings 
# Note: dynamic hook registration for WaitNode needs access to shared.command_hooks?
# Or we move command_hooks to context?
# For now, command_hooks are global in shared.py. 
# We should probably access them via shared or pass them in context.
# Refactoring plan says "Reducing Global State", so ideally context should hold it.
# usage of shared.command_hooks is deep in discord_manager.
# Let's import shared for now to keep it working, refactor later.
import shared

class DiscordSendNode(NodeHandler):
    @property
    def node_type(self): return "discord_send"
    
    def execute(self, node: Dict[str, Any], context: RuntimeContext) -> Optional[str]:
        props = node.get('properties', {})
        msg = props.get('message', '')
        try:
            settings = load_settings()
            uid = settings.get('user_id')
            
            if context.discord_client and uid:
                async def _send_dm():
                    try:
                        await context.discord_client.wait_until_ready()
                        user = await context.discord_client.fetch_user(int(uid))
                        await user.send(msg)
                        log_message(f"Sent DM to {uid}: {msg}")
                    except Exception as exc:
                        log_message(f"Failed to send DM: {exc}")
                
                if context.discord_loop:
                    future = asyncio.run_coroutine_threadsafe(_send_dm(), context.discord_loop)
                    try:
                         future.result(timeout=15)
                    except Exception as fe:
                         log_message(f"Discord Send Timed Out/Failed: {fe}")
                else:
                     log_message("Discord loop not active.")
            else:
                log_message("Skipped Discord Send: No client or User ID.")
        except Exception as e:
            log_message(f"Discord Send Error: {e}")
            
        return node.get('next')

class DiscordScreenshotNode(NodeHandler):
    @property
    def node_type(self): return "discord_screenshot"
    
    def execute(self, node: Dict[str, Any], context: RuntimeContext) -> Optional[str]:
        props = node.get('properties', {})
        msg = props.get('message', '')
        temp_path = "temp_screenshot_discord.png"
        
        # 1. Capture
        try:
            context.bot.screencap(temp_path)
        except Exception as e:
            log_message(f"Screenshot capture failed: {e}")
            
        # 2. Send
        if os.path.exists(temp_path):
            try:
                settings = load_settings()
                uid = settings.get('user_id')
                if context.discord_client and uid:
                    async def _send_dm_img():
                        try:
                            await context.discord_client.wait_until_ready()
                            user = await context.discord_client.fetch_user(int(uid))
                            with open(temp_path, 'rb') as f:
                                picture = discord.File(f, filename="screenshot.png")
                                await user.send(content=msg, file=picture)
                            log_message(f"Sent Screenshot to {uid}")
                        except Exception as exc:
                            log_message(f"Failed to send Screenshot: {exc}")
                    
                    if context.discord_loop:
                        future = asyncio.run_coroutine_threadsafe(_send_dm_img(), context.discord_loop)
                        try:
                            future.result(timeout=20)
                        except Exception as fe:
                            log_message(f"Discord Screenshot Timed Out/Failed: {fe}")
                    else:
                        log_message("Discord loop not active.")
                else:
                    log_message("Skipped Discord Screenshot: No client or User ID.")
            except Exception as e:
                log_message(f"Discord Screenshot Error: {e}")
            
            # Cleanup
            try: os.remove(temp_path)
            except: pass
            
        return node.get('next')

class DiscordWaitNode(NodeHandler):
    @property
    def node_type(self): return "discord_wait"
    
    def execute(self, node: Dict[str, Any], context: RuntimeContext) -> Optional[str]:
        props = node.get('properties', {})
        cmd_name = props.get('command_name', 'continue')
        node_id = node['id']
        log_message(f"Waiting for Discord command: /{cmd_name} ...")
        
        # Create event
        event = threading.Event()
        # We store event in CONTEXT now, not shared globa (ideally)
        # But global hook needs to find it. 
        # If we use shared.wait_events, it works globally.
        # If we use context.wait_events, we need to register the hook such that it knows which context to trigger.
        # Currently the 'signaler' in runtime dynamic registration might need access to it.
        # For this refactor, let's keep using shared.wait_events for compatibility with existing hooks,
        # OR fully migrate hooks to be context-aware.
        # Since 'run_script' in listener registers hooks that signal `shared.wait_events`.
        # We should stick to shared.wait_events OR update run_script.
        # To strictly follow "migrate to context", we utilize context.wait_events.
        # BUT, the listener runs in Discord thread/loop. It doesn't know about 'RuntimeContext'.
        # So we probably need to maintain shared.wait_events as the bridge.
        
        shared.wait_events[node_id] = event
        
        wait_success = False
        while context.is_running:
            if event.wait(timeout=1.0):
                wait_success = True
                break
        
        shared.wait_events.pop(node_id, None)
        
        if wait_success:
            log_message(f"Resumed by command /{cmd_name}")
            return node.get('next')
        else:
            log_message("Wait cancelled (Script Stopped).")
            return None
