"""
MoreLogin CDP Stress Test
==========================

Description:
    Stress test for MoreLogin browser automation via CDP (Chrome DevTools Protocol).
    Runs N concurrent tasks with configurable concurrency. Each task:
      1. Creates a browser profile
      2. Starts the browser (headless)
      3. Sets up socat port forwarding (remote → local)
      4. Connects via CDP using Playwright
      5. Opens a page and takes a screenshot
      6. Cleans up all resources

    Reports success/failure statistics at the end.

Prerequisites:
    pip install requests playwright paramiko
    playwright install chromium

Usage:
    python stress_test_cdp.py

Configuration:
    Modify the "Configuration" section below to match your environment.
"""

import random
import subprocess
import time
import traceback
from datetime import datetime
from pathlib import Path

import asyncio
from playwright.async_api import async_playwright, Playwright

from base_morelogin.base_func import requestHeader, postRequest


# ==================== Configuration ====================

# MoreLogin API credentials (get from profile list page → API button)
APPID = '1606746458587128'
SECRETKEY = '29d7c664af4f4963af67c4bb22a74d75'

# MoreLogin server address
BASEURL = 'http://192.168.226.131:40000'

# CDP connection host (same as MoreLogin server)
CDP_HOST = '192.168.226.131'

# SSH config for remote socat port forwarding
SSH_USER = 'kxc'
SSH_HOST = CDP_HOST
SSH_PORT = 22
SSH_PASSWORD = 'root'
SSH_KEY_PATH = ''  # Path to SSH private key (leave empty to use password)

# Stress test parameters
CONCURRENCY = 5    # Max number of concurrent browser sessions
TOTAL_RUNS = 100   # Total number of tasks to execute

# Retry & timeout settings
MAX_RETRIES = 5           # Max retries for API calls
CDP_CONNECT_TIMEOUT = 30  # CDP connection timeout (seconds)
PAGE_TIMEOUT = 60         # Page load timeout (seconds)


# ==================== SSH & Socat Port Forwarding ====================

class SocatForwarder:
    """
    Manages socat port forwarding on a remote server via SSH.

    MoreLogin binds debug ports to 127.0.0.1 by default. This class sets up
    socat on the remote server to forward a public port to the local debug port,
    enabling CDP connections from external machines.
    """

    @staticmethod
    def start(task_id: int, original_port: int) -> tuple:
        """
        Start socat port forwarding on the remote server.

        Args:
            task_id: Task identifier for logging
            original_port: The original CDP debug port (bound to 127.0.0.1)

        Returns:
            (forward_port, remote_pid): The public port and remote process ID.
            If forwarding fails, returns (original_port, None).
        """
        # Use random high port to avoid collisions between concurrent tasks
        forward_port = random.randint(50000, 60000)
        remote_cmd = (
            f'nohup socat TCP-LISTEN:{forward_port},fork,reuseaddr,bind=0.0.0.0 '
            f'TCP:127.0.0.1:{original_port} >/dev/null 2>&1 & echo $!'
        )

        try:
            output = SSHClient.exec_command(remote_cmd)
            if output is None:
                print(f'[Task {task_id}] socat: SSH command failed, using original port')
                return int(original_port), None

            remote_pid = output.strip()
            if not remote_pid.isdigit():
                print(f'[Task {task_id}] socat: unexpected output: {output}')
                return int(original_port), None

            print(f'[Task {task_id}] socat: forwarding 0.0.0.0:{forward_port} → 127.0.0.1:{original_port} (pid={remote_pid})')
            return forward_port, remote_pid

        except Exception as e:
            print(f'[Task {task_id}] socat: error - {e}')
            return int(original_port), None

    @staticmethod
    def stop(remote_pid: str):
        """
        Stop socat port forwarding by killing the remote process.

        Args:
            remote_pid: The PID of the socat process on the remote server.
        """
        if remote_pid is None:
            return
        remote_cmd = f'kill {remote_pid} 2>/dev/null; sleep 0.5; kill -9 {remote_pid} 2>/dev/null; echo done'
        try:
            SSHClient.exec_command(remote_cmd)
        except Exception:
            pass


class SSHClient:
    """
    SSH client for executing commands on the remote MoreLogin server.
    Supports paramiko (cross-platform) with fallback to system ssh command.
    """

    @staticmethod
    def exec_command(remote_cmd: str) -> str:
        """
        Execute a command on the remote server via SSH.

        Args:
            remote_cmd: Shell command to execute remotely.

        Returns:
            Command stdout output, or None on failure.
        """
        try:
            import paramiko
            return SSHClient._exec_paramiko(remote_cmd)
        except ImportError:
            return SSHClient._exec_system(remote_cmd)

    @staticmethod
    def _exec_paramiko(remote_cmd: str) -> str:
        """Execute via paramiko SSH library (works on all platforms)."""
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            'hostname': SSH_HOST,
            'port': SSH_PORT,
            'username': SSH_USER,
            'timeout': 10,
        }
        if SSH_KEY_PATH:
            connect_kwargs['key_filename'] = SSH_KEY_PATH
        elif SSH_PASSWORD:
            connect_kwargs['password'] = SSH_PASSWORD

        try:
            client.connect(**connect_kwargs)
            stdin, stdout, stderr = client.exec_command(remote_cmd, timeout=15)
            return stdout.read().decode('utf-8')
        finally:
            client.close()

    @staticmethod
    def _exec_system(remote_cmd: str) -> str:
        """Execute via system ssh binary (Linux/macOS fallback)."""
        ssh_cmd = [
            'ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10',
            '-p', str(SSH_PORT),
        ]
        if SSH_KEY_PATH:
            ssh_cmd += ['-i', SSH_KEY_PATH]
        ssh_cmd += [f'{SSH_USER}@{SSH_HOST}', remote_cmd]

        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return None
        return result.stdout


# ==================== MoreLogin API Operations ====================

class MoreLoginAPI:
    """
    Wrapper for MoreLogin REST API operations used in stress testing.

    API Documentation:
        https://docs.morelogin.com/l/en/interface-documentation/browser-profile
    """

    @staticmethod
    def create_profile() -> str:
        """
        Create a browser profile with retry logic.

        Returns:
            envId (str) on success, None on failure.
        """
        request_path = '/api/env/create/advanced'
        data = {
            "browserTypeId": 1,
            "operatorSystemId": 5,
            "startupParams": ["--no-sandbox"]
        }

        for attempt in range(MAX_RETRIES):
            headers = requestHeader(APPID, SECRETKEY)
            headers['Content-Type'] = 'application/json'
            response = postRequest(BASEURL + request_path, data, headers=headers).json()

            if response['code'] == 0 and response.get('data'):
                return response['data']

            if attempt < MAX_RETRIES - 1:
                wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                print(f"  [create_profile] Attempt {attempt + 1} failed (code={response['code']}), "
                      f"retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)

        return None

    @staticmethod
    def start_profile(env_id: str) -> tuple:
        """
        Start a browser profile in headless mode.

        Args:
            env_id: The profile ID to start.

        Returns:
            (cdp_url, debug_port) tuple.

        Raises:
            RuntimeError: If the API returns an error.
        """
        request_path = BASEURL + '/api/env/start'
        data = {
            'envId': env_id,
            'uniqueId': '',
            'isHeadless': True
        }
        headers = requestHeader(APPID, SECRETKEY)
        response = postRequest(request_path, data, headers).json()

        if response['code'] != 0:
            raise RuntimeError(f"Start profile failed: {response.get('msg', 'unknown error')}")

        port = response['data']['debugPort']
        cdp_url = f'http://{CDP_HOST}:{port}'
        return cdp_url, port

    @staticmethod
    def stop_profile(env_id: str) -> bool:
        """
        Stop (close) a running browser profile.

        Args:
            env_id: The profile ID to stop.

        Returns:
            True on success, False on failure.
        """
        request_path = '/api/env/close'
        data = {'envId': env_id, 'uniqueId': ''}
        headers = requestHeader(APPID, SECRETKEY)
        response = postRequest(BASEURL + request_path, data, headers).json()
        return response['code'] != -1

    @staticmethod
    def delete_profile(env_id: str) -> bool:
        """
        Delete a browser profile (move to recycle bin with data removal).

        Args:
            env_id: The profile ID to delete.

        Returns:
            True on success, False on failure.
        """
        request_path = '/api/env/removeToRecycleBin/batch'
        data = {"envIds": [env_id], "removeEnvData": True}

        for attempt in range(MAX_RETRIES):
            headers = requestHeader(APPID, SECRETKEY)
            headers['Content-Type'] = 'application/json'
            response = postRequest(BASEURL + request_path, data, headers).json()

            if response['code'] == 0 and response.get('data'):
                return True

            if attempt < MAX_RETRIES - 1:
                wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                time.sleep(wait_time)

        return False


# ==================== Single Task Execution ====================

async def run_single_task(task_id: int, playwright: Playwright) -> tuple:
    """
    Execute a single stress test task (full lifecycle).

    Workflow:
        1. Create profile → 2. Start browser → 3. Setup socat forwarding
        → 4. Connect CDP → 5. Navigate & screenshot → 6. Cleanup

    Args:
        task_id: Unique task identifier for logging.
        playwright: Shared Playwright instance.

    Returns:
        (success: bool, error_msg: str or None)
    """
    env_id = None
    remote_pid = None
    screenshot_path = None

    try:
        # Step 1: Create browser profile
        env_id = MoreLoginAPI.create_profile()
        if not env_id:
            return False, "Failed to create profile after retries"
        print(f'[Task {task_id}] Profile created: {env_id}')

        # Step 2: Start browser profile (headless)
        cdp_url, original_port = MoreLoginAPI.start_profile(env_id)
        print(f'[Task {task_id}] Browser started, debug port: {original_port}')

        # Step 3: Setup socat port forwarding
        forward_port, remote_pid = SocatForwarder.start(task_id, original_port)
        await asyncio.sleep(3)  # Wait for socat to be ready

        cdp_url_final = f'http://{CDP_HOST}:{forward_port}' if remote_pid else cdp_url

        # Step 4: Connect via CDP (with retries)
        browser = None
        for attempt in range(MAX_RETRIES):
            try:
                browser = await playwright.chromium.connect_over_cdp(
                    cdp_url_final, timeout=CDP_CONNECT_TIMEOUT * 1000
                )
                break
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f'[Task {task_id}] CDP connect attempt {attempt + 1} failed, retrying...')
                    await asyncio.sleep(3 + attempt)
                else:
                    raise RuntimeError(f"CDP connection failed after {MAX_RETRIES} attempts: {e}")

        # Step 5: Navigate and take screenshot
        context = browser.contexts[0]
        page = await context.new_page()
        await page.goto('https://www.google.com', timeout=PAGE_TIMEOUT * 1000)
        await page.wait_for_load_state('load', timeout=PAGE_TIMEOUT * 1000)

        screenshot_dir = Path(__file__).resolve().parent / 'screenshots'
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_path = screenshot_dir / f"stress_task{task_id}_{timestamp}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True, timeout=PAGE_TIMEOUT * 1000)
        print(f'[Task {task_id}] Screenshot saved: {screenshot_path.name}')

        await page.close()
        await browser.close()

        print(f'[Task {task_id}] ✓ SUCCESS')
        return True, None

    except Exception as e:
        error_msg = traceback.format_exc()
        print(f'[Task {task_id}] ✗ FAILED: {e}')
        return False, error_msg

    finally:
        # Cleanup: stop socat forwarding
        SocatForwarder.stop(remote_pid)

        # Cleanup: close browser profile
        if env_id:
            try:
                MoreLoginAPI.stop_profile(env_id)
            except Exception:
                pass

        # Cleanup: delete browser profile
        if env_id:
            try:
                await asyncio.sleep(1)
                MoreLoginAPI.delete_profile(env_id)
                print(f'[Task {task_id}] Profile deleted: {env_id}')
            except Exception:
                pass

        # Cleanup: remove screenshot (only needed for verification)
        if screenshot_path and screenshot_path.exists():
            try:
                screenshot_path.unlink()
            except Exception:
                pass


# ==================== Main Entry Point ====================

async def main():
    """
    Run the stress test with configured concurrency and total runs.
    Uses asyncio.Semaphore to limit concurrent browser sessions.
    """
    print("=" * 60)
    print(f"  MoreLogin CDP Stress Test")
    print(f"  Concurrency: {CONCURRENCY} concurrent sessions")
    print(f"  Total runs:  {TOTAL_RUNS}")
    print(f"  Target:      {CDP_HOST}")
    print("=" * 60)
    print()

    start_time = time.time()
    results = []  # [(task_id, success, error_msg)]
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def worker(task_id: int, pw: Playwright):
        """Worker coroutine that respects concurrency limit."""
        async with semaphore:
            success, error_msg = await run_single_task(task_id, pw)
            results.append((task_id, success, error_msg))

    async with async_playwright() as playwright:
        tasks = [worker(i + 1, playwright) for i in range(TOTAL_RUNS)]
        await asyncio.gather(*tasks)

    elapsed = time.time() - start_time

    # Print statistics
    success_count = sum(1 for _, s, _ in results if s)
    failure_count = TOTAL_RUNS - success_count

    print()
    print("=" * 60)
    print(f"  Stress Test Results")
    print("=" * 60)
    print(f"  Total runs:     {TOTAL_RUNS}")
    print(f"  Concurrency:    {CONCURRENCY}")
    print(f"  Succeeded:      {success_count}")
    print(f"  Failed:         {failure_count}")
    print(f"  Success rate:   {success_count / TOTAL_RUNS * 100:.1f}%")
    print(f"  Total time:     {elapsed:.2f}s")
    print(f"  Avg time/task:  {elapsed / TOTAL_RUNS:.2f}s")
    print(f"  Throughput:     {TOTAL_RUNS / elapsed:.2f} tasks/s")
    print("=" * 60)

    # Print failure details
    if failure_count > 0:
        print()
        print("  Failed task details:")
        print("-" * 60)
        for task_id, success, error_msg in results:
            if not success:
                # Show first 200 chars of error
                short_err = (error_msg or 'Unknown error').strip().split('\n')[-1][:200]
                print(f"  [Task {task_id}] {short_err}")
        print()


if __name__ == '__main__':
    asyncio.run(main())
