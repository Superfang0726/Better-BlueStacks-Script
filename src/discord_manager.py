import discord
from discord import app_commands
import asyncio
import threading
import time
import shared
from shared import log_message
from engine import execute_graph, get_bot
from settings import load_settings

def run_discord_bot_thread(token):
    """
    Background thread to run the persistent Discord Bot.
    """
    log_message("Starting Persistent Discord Bot...")
    
    intents = discord.Intents.default()
    # Set status and activity immediately upon client creation
    client = discord.Client(
        intents=intents,
        status=discord.Status.online,
        activity=discord.Game(name="BrownFarm Script")
    )
    tree = app_commands.CommandTree(client)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    shared.discord_client = client
    shared.discord_tree = tree
    shared.discord_loop = loop
    
    @client.event
    async def on_ready():
        log_message(f"Discord Bot Logged in as {client.user} (Persistent)")
        await client.wait_until_ready() # Ensure internal cache is ready
        # Status is now set in __init__
        await tree.sync()
        
        # Load commands from settings
        settings = load_settings()
        commands_config = settings.get('commands', [])
        
        if commands_config:
            log_message(f"Registering {len(commands_config)} declared commands...")
            # We clear commands to ensure clean slate based on settings
            tree.clear_commands(guild=None)
            
            for cmd in commands_config:
                c_name = cmd.get('name', '').strip()
                c_desc = cmd.get('desc', '').strip()
                if not c_desc: c_desc = "Script command"
                
                if not c_name: continue
                
                # Generic Callback that delegates to shared.command_hooks
                # We use a factory to capture c_name
                def make_handler(name_captured):
                     async def _generic_handler(interaction: discord.Interaction):
                         log_message(f"Command triggered: /{name_captured}")
                         
                         handler = shared.command_hooks.get(name_captured)
                         if handler:
                             # Execute handler (could be running script or signaling event)
                             # Handler returns a message or boolean? Let's say handler handles its own logic, 
                             # but here we need to acknowledge interaction.
                             await interaction.response.send_message(f"Command /{name_captured} received...", ephemeral=True)
                             result = handler()
                             if result is False: # Explicit False
                                 pass # Handler failed?
                         else:
                             await interaction.response.send_message(f"Command /{name_captured} is declared, but no running script is handling it.", ephemeral=True)
                     return _generic_handler
                
                command = app_commands.Command(name=c_name, description=c_desc, callback=make_handler(c_name))
                tree.add_command(command)
            
            try:
                await tree.sync()
                log_message("Commands synced with Discord.")
                
                # Notify user to refresh
                user_id_raw = settings.get('user_id')
                if user_id_raw:
                    try:
                        user_id = int(str(user_id_raw).strip()) # Ensure int
                        user = await client.fetch_user(user_id)
                        if user:
                            await user.send(
                                "✅ **Bot Commands Updated!**\n"
                                "If you don't see the new commands:\n"
                                "💻 **PC**: Press `Ctrl + R` to refresh Discord.\n"
                                "📱 **Mobile**: Completely restart the App.",
                                silent=True
                            )
                    except ValueError:
                        log_message(f"Invalid User ID format: {user_id_raw}")
                    except Exception as ux:
                        log_message(f"Could not send DM to user (ID: {user_id_raw}): {ux}")
                        
            except Exception as e:
                log_message(f"Failed to sync commands: {e}")
        else:
            log_message("No declared commands found in settings.")

    async def runner():
        async with client:
            await client.start(token)

    try:
        loop.run_until_complete(runner())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        log_message(f"Discord Bot Error: {e}")
    finally:
        loop.close()
        log_message("Discord Bot Loop Closed")

def start_bot_background(token=None):
    if not token:
        settings = load_settings()
        token = settings.get('discord_token')
    
    if not token:
        log_message("No Discord Token found. Bot not started.")
        return

    if shared.discord_client and not shared.discord_client.is_closed():
        log_message("Discord Bot is already running.")
        return

    shared.discord_thread = threading.Thread(target=run_discord_bot_thread, args=(token,))
    shared.discord_thread.daemon = True # Kill when main server stops
    shared.discord_thread.start()

def stop_bot():
    if shared.discord_client and shared.discord_loop and not shared.discord_client.is_closed():
        asyncio.run_coroutine_threadsafe(shared.discord_client.close(), shared.discord_loop)
    log_message("Discord Bot Stop Requested.")

# Old explicitly registration function removed as we now use declarative settings

def run_script(actions, mode='graph'):
    """
    Main entry point for running a script.
    執行腳本的主要入口點。
    """
    shared.is_running = True
    # Clear old hooks
    shared.command_hooks.clear()
    
    log_message(f"Starting execution...")
    
    try:
        get_bot()
            
        # Identify nodes
        start_node = next((n for n in actions if n.get('type') == 'start'), None)
        slash_nodes = [n for n in actions if n.get('type') == 'discord_slash']
        wait_nodes = [n for n in actions if n.get('type') == 'discord_wait']
        # Support namespaced types too just in case
        if not slash_nodes: slash_nodes = [n for n in actions if n.get('type') == 'bot/discord_slash']
        if not wait_nodes: wait_nodes = [n for n in actions if n.get('type') == 'bot/discord_wait']

        # 1. Register Runtime Hooks
        # Map command_name -> Logic
        for node in slash_nodes:
            cmd_name = node['properties'].get('command_name', '').strip()
            if not cmd_name: 
                log_message(f"Warning: Slash Node {node['id']} has no command name. Skipping.")
                continue
            
            if cmd_name in shared.command_hooks:
                log_message(f"Warning: Command '/{cmd_name}' (Node {node['id']}) overwrites previous handler!")
            
            node_id = node['id']
            # Logic: Start subgraph
            def runner():
                threading.Thread(target=execute_graph, args=(actions,), kwargs={'start_node_id': node_id}).start()
            
            shared.command_hooks[cmd_name] = runner



        for node in wait_nodes:
            cmd_name = node['properties'].get('command_name', 'continue').strip()
            if not cmd_name: cmd_name = 'continue'
            
            if cmd_name in shared.command_hooks:
                log_message(f"Warning: Command '/{cmd_name}' (WaitNode {node['id']}) overwrites previous handler! Check for duplicates.")

            node_id = node['id']
            # Logic: Signal Wait Event
            # Fix closure capture by using default argument
            def signaler(nid=node_id, nm=cmd_name):
                event = shared.wait_events.get(nid)
                if event:
                    log_message(f"Signaling event for node {nid}")
                    event.set()
                    return True
                else:
                    log_message(f"Command '/{nm}' received, but WaitNode {nid} is not waiting (Event not found).")
                return False
            
            shared.command_hooks[cmd_name] = signaler
            log_message(f"Registered Wait Command: /{cmd_name} -> Node {node_id}")

        # 2. Start Execution
        if start_node:
            execute_graph(actions)
        elif slash_nodes:
             log_message("Listening for Slash Commands... (Press Stop to end)")
             while shared.is_running:
                 time.sleep(1)
        else:
             log_message("Error: No Start Node and No Slash Commands found.")
            
    except Exception as e:
        log_message(f"Script execution error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        shared.is_running = False
        shared.command_hooks.clear() # Cleanup
        log_message("Script stopped.")
