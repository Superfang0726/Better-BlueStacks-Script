"""
Auto-update checker for Better BlueStacks Script.
Checks GitHub for updates and prompts user to update if available.
"""
import subprocess
import sys
import os

def run_git_command(args, capture=True):
    """Run a git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=capture,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except FileNotFoundError:
        return False, "", "Git not found"
    except Exception as e:
        return False, "", str(e)

def check_for_updates():
    """
    Check if there are updates available on the remote repository.
    Returns: (has_updates: bool, local_changes: bool, message: str)
    """
    print("[INFO] Checking for updates...")
    
    # Check if this is a git repository
    success, _, _ = run_git_command(["rev-parse", "--git-dir"])
    if not success:
        return False, False, "Not a git repository"
    
    # Check for local modifications
    success, status_output, _ = run_git_command(["status", "--porcelain"])
    if not success:
        return False, False, "Failed to check git status"
    
    has_local_changes = bool(status_output.strip())
    
    # Fetch latest from remote
    print("[INFO] Fetching latest changes from GitHub...")
    success, _, err = run_git_command(["fetch", "origin"])
    if not success:
        return False, has_local_changes, f"Failed to fetch: {err}"
    
    # Get current branch
    success, branch, _ = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
    if not success:
        branch = "main"
    
    # Compare local and remote
    success, local_hash, _ = run_git_command(["rev-parse", "HEAD"])
    success2, remote_hash, _ = run_git_command(["rev-parse", f"origin/{branch}"])
    
    if not success or not success2:
        return False, has_local_changes, "Failed to compare versions"
    
    if local_hash == remote_hash:
        return False, has_local_changes, "Already up to date"
    
    # Get commit count difference
    success, behind_count, _ = run_git_command(["rev-list", "--count", f"HEAD..origin/{branch}"])
    
    return True, has_local_changes, f"{behind_count} new commit(s) available"

def perform_update(is_docker=False):
    """
    Perform the update by pulling from remote.
    For Docker, also triggers a rebuild.
    Returns: (success: bool, message: str)
    """
    print("[INFO] Pulling latest changes...")
    
    success, output, err = run_git_command(["pull", "origin"])
    if not success:
        return False, f"Failed to pull: {err}"
    
    print(f"[OK] {output}")
    
    # Check if requirements.txt was updated
    success, changed_files, _ = run_git_command(["diff", "--name-only", "HEAD@{1}", "HEAD"])
    
    if "requirements.txt" in changed_files:
        print("[INFO] requirements.txt was updated, dependencies will be reinstalled.")
        if not is_docker:
            # For non-Docker, reinstall dependencies
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
                print("[OK] Dependencies updated")
            except Exception as e:
                print(f"[WARN] Failed to update dependencies: {e}")
    
    if is_docker:
        print("[INFO] Docker image will be rebuilt on next start.")
    
    return True, "Update completed successfully"

def main():
    """Main entry point for update checker."""
    # Check command line args
    is_docker = "--docker" in sys.argv
    skip_prompt = "--auto" in sys.argv
    
    print()
    print("========================================")
    print("       Checking for Updates...")
    print("========================================")
    print()
    
    has_updates, has_local_changes, message = check_for_updates()
    
    if not has_updates:
        print(f"[OK] {message}")
        print()
        return 0
    
    # Updates available
    print(f"[UPDATE] {message}")
    print()
    
    if has_local_changes:
        print("[WARN] You have local modifications that are not committed.")
        print("[WARN] Update skipped to prevent conflicts.")
        print("[WARN] If you want to update, please commit or discard your changes first.")
        print()
        return 0
    
    if skip_prompt:
        # Auto mode - just update
        success, msg = perform_update(is_docker)
        print(f"{'[OK]' if success else '[ERROR]'} {msg}")
        return 0 if success else 1
    
    # Prompt user
    print("Do you want to update now?")
    choice = input("Update? (Y/N): ").strip().lower()
    
    if choice in ['y', 'yes', '是']:
        success, msg = perform_update(is_docker)
        print(f"{'[OK]' if success else '[ERROR]'} {msg}")
        if success:
            print()
            print("[INFO] Please restart the application to use the new version.")
        return 0 if success else 1
    else:
        print("[INFO] Update skipped.")
        return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[INFO] Update check cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Update check failed: {e}")
        sys.exit(1)
