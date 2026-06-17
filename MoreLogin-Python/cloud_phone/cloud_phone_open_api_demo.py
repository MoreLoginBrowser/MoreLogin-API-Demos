import os
import time
import requests
from requests.adapters import HTTPAdapter


class MoreLoginCloudPhone:
    """
    MoreLogin Cloud Phone Open API Client.

    This class provides a Python wrapper for the MoreLogin Cloud Phone Open API.
    All requests are sent to the public API endpoint: https://api.morelogin.com

    Usage:
        client = MoreLoginCloudPhone(app_id="YOUR_APP_ID", api_key="YOUR_API_KEY")
        devices = client.list_devices()

    You can obtain your app_id and api_key from the MoreLogin client under API & MCP settings.
    """

    def __init__(self, app_id: str, api_key: str):
        self.APP_ID = app_id
        self.API_KEY = api_key
        self.HOST = "https://api.morelogin.com"
        self.__data = {}
        self.__token_expire_time = 0  # Token expiration timestamp

        self.__session = requests.Session()
        adapter = HTTPAdapter(pool_connections=50, pool_maxsize=500, max_retries=1)
        self.__session.mount('http://', adapter)
        self.__session.mount('https://', adapter)
        self.__session.trust_env = False
        self.__session.allow_redirects = False

    def get_token(self, timeout=10):
        """
        Obtain an access token for API authentication.

        The token is valid for 3600 seconds (1 hour). It will be refreshed automatically
        60 seconds before expiration to avoid using an expired token.

        Args:
            timeout: Request timeout in seconds (default: 10).

        Returns:
            str: The access token string, or empty string if failed.
        """
        access_token = ""
        url = f"{self.HOST}/oauth2/token"
        payload = {
            "client_id": self.APP_ID,
            "client_secret": self.API_KEY,
            "grant_type": "client_credentials"
        }
        headers = {"Content-Type": "application/json"}
        try:
            data_json = self.__session.post(url, json=payload, headers=headers, timeout=timeout).json()
            if data_json.get("code") == 0:
                access_token = data_json.get('data', {}).get('access_token')
                # Record token expiration time, refresh 60 seconds early to avoid edge-case expiry
                expires_in = data_json.get('data', {}).get('expires_in', 3600)
                self.__token_expire_time = time.time() + expires_in - 60
        except Exception as e:
            print(f"[ERROR] Failed to get token: {e}")
        return access_token

    def _post(self, url_path: str, payload, timeout=10):
        """
        Internal method to send authenticated POST requests.

        Automatically obtains and refreshes the access token when needed.

        Args:
            url_path: API endpoint path (e.g., "/cloudphone/page").
            payload: Request body (dict or list).
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: The JSON response from the API.
        """
        data = {}
        try:
            # Auto-obtain token on first call, or refresh if expired
            if "access_token" not in self.__data or time.time() >= self.__token_expire_time:
                if time.time() >= self.__token_expire_time and "access_token" in self.__data:
                    print("[INFO] Token expired, refreshing...")
                access_token = self.get_token(timeout)
                if not access_token:
                    print("[ERROR] Failed to obtain access_token")
                    return data
                self.__data['access_token'] = access_token

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.__data['access_token']}"
            }
            data = self.__session.post(
                f"{self.HOST}{url_path}", json=payload, headers=headers, timeout=timeout
            ).json()
        except Exception as e:
            print(f"[ERROR] Request to {url_path} failed: {e}")
        return data

    # ======================== Device Management ========================

    def list_devices(self, page_no: int = 1, page_size: int = 1000, timeout=10):
        """
        List cloud phones under the account.

        API: POST /cloudphone/page

        Args:
            page_no: Page number, starting from 1 (default: 1).
            page_size: Number of items per page (default: 1000).
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response containing paginated device list.
                  Response format: {"code": 0, "data": {"total": "N", "dataList": [...]}, "requestId": "..."}
        """
        payload = {
            "pageNo": page_no,
            "pageSize": page_size,
        }
        return self._post("/cloudphone/page", payload=payload, timeout=timeout)

    def get_device_info(self, phone_id, timeout=10):
        """
        Get detailed information and status of a cloud phone.

        API: POST /cloudphone/info

        The envStatus field indicates the device state:
            - 2: Powered off
            - 4: Powered on (ready)
            - 7: New machine reset in progress

        Args:
            phone_id: Cloud phone ID (str or int).
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response with device details including status, proxy, settings, etc.
        """
        return self._post("/cloudphone/info", payload={"id": phone_id}, timeout=timeout)

    def get_device_info_by_android_id(self, android_id, timeout=10):
        """
        Get cloud phone details by Android ID.

        API: POST /cloudphone/queryByAndroidId

        Args:
            android_id: The Android ID of the device (str or int).
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response with device details.
        """
        return self._post("/cloudphone/queryByAndroidId", payload={"androidId": android_id}, timeout=timeout)

    # ======================== Power Management ========================

    def power_on(self, phone_id, extra_payload: dict = None, timeout=10):
        """
        Power on a cloud phone.

        API: POST /cloudphone/powerOn

        Args:
            phone_id: Cloud phone ID (str or int).
            extra_payload: Optional additional fields (e.g., {"proxyId": 123456789} to specify a proxy on boot).
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response.
                  - code=0: Power on command sent successfully.
                  - code=33324: The device is already running.
        """
        payload = {"id": phone_id}
        if extra_payload:
            payload.update(extra_payload)
        return self._post("/cloudphone/powerOn", payload=payload, timeout=timeout)

    def power_off(self, phone_id, timeout=10):
        """
        Power off a cloud phone.

        API: POST /cloudphone/powerOff

        Args:
            phone_id: Cloud phone ID (str or int).
            timeout: Request timeout in seconds (default: 10).

        Returns:
            bool: True if the device was powered off (or was already off), None otherwise.
                  - code=0: Successfully powered off.
                  - code=33301: Device was already off (treated as success).
        """
        payload = {"id": phone_id}
        data = self._post("/cloudphone/powerOff", payload=payload, timeout=timeout)
        if data.get('code', -1) in (0, 33301):
            return True

    def wait_until_ready(self, phone_id, timeout_seconds=300, callback=None, poll_interval=5, timeout=10):
        """
        Poll the device status until it is fully powered on (envStatus=4).

        Args:
            phone_id: Cloud phone ID (str or int).
            timeout_seconds: Maximum time to wait in seconds (default: 300 = 5 minutes).
            callback: Optional callback function for status messages. If None, prints to stdout.
            poll_interval: Polling interval in seconds (default: 5).
            timeout: Request timeout for each status query (default: 10).

        Returns:
            dict: Device info response if powered on successfully.
            False: If timed out waiting for the device.
        """
        start_time = int(time.time())
        while True:
            info_data = self.get_device_info(phone_id, timeout)
            env_status = info_data.get('data', {}).get('envStatus')
            if env_status == 4:
                msg = "Device is ready (powered on)"
                callback(msg) if callback else print(f"[INFO] {msg}")
                time.sleep(1)
                return info_data

            elapsed = int(time.time()) - start_time
            msg = f"Waiting for device to power on... elapsed: {elapsed}s"
            callback(msg) if callback else print(f"[INFO] {msg}")

            if elapsed >= timeout_seconds:
                msg = f"Timed out after {timeout_seconds}s waiting for device to power on"
                callback(msg) if callback else print(f"[WARN] {msg}")
                time.sleep(1)
                return False
            time.sleep(poll_interval)

    def new_machine(self, phone_id, timeout=10):
        """
        Reset the cloud phone to a new device profile (one-click new machine).

        This randomizes device fingerprint information. The device must be powered on
        (envStatus=4) before calling this method.

        API: POST /cloudphone/newMachine

        Args:
            phone_id: Cloud phone ID (str or int).
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response.
                  - code=0: New machine reset initiated.
                  - code=33301: Device is not powered on (must power on first).
        """
        payload = {"id": phone_id}
        return self._post("/cloudphone/newMachine", payload=payload, timeout=timeout)

    # ======================== Proxy Management ========================

    def set_proxy(self, phone_id, proxy_type: int, host: str, port: int, username: str, password: str, timeout=20):
        """
        Set proxy configuration for a cloud phone.

        API: POST /cloudphone/setProxy
        Docs: https://guide.morelogin.com/api-reference/cloud-phone/open-api/cloud-phone-management/setproxy

        Args:
            phone_id: Cloud phone ID (str or int).
            proxy_type: Proxy protocol type — 0: HTTP, 1: HTTPS, 2: SOCKS5.
            host: Proxy server hostname or IP.
            port: Proxy server port.
            username: Proxy authentication username.
            password: Proxy authentication password.
            timeout: Request timeout in seconds (default: 20).

        Returns:
            dict: API response.
        """
        payload = {
            "ids": [phone_id],
            "proxy": {
                "proxyProvider": proxy_type,
                "proxyIp": host,
                "proxyPort": port,
                "username": username,
                "password": password
            }
        }
        return self._post("/cloudphone/setProxy", payload=payload, timeout=timeout)

    def delete_proxy(self, proxy_id, timeout=10):
        """
        Delete a proxy configuration.

        API: POST /proxyInfo/delete

        Args:
            proxy_id: The proxy ID to delete (str or int).
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response.
        """
        return self._post("/proxyInfo/delete", payload=[proxy_id], timeout=timeout)

    # ======================== App Management ========================

    def list_installed_apps(self, phone_id, timeout=10):
        """
        List all installed apps on a cloud phone.

        API: POST /cloudphone/app/installedList

        Args:
            phone_id: Cloud phone ID (str or int).
            timeout: Request timeout in seconds (default: 10).

        Returns:
            list: List of installed app dicts, each containing appName, packageName,
                  versionCode, versionName, etc. Returns empty list on failure.
        """
        data_list = []
        response = self._post("/cloudphone/app/installedList", payload={"id": phone_id}, timeout=timeout)
        if response.get('code', -1) == 0:
            data_list = response.get('data', [])
        return data_list

    def search_and_install_app(self, phone_id, app_name=None, version_name=None, timeout=10):
        """
        Search for available apps and install them on a cloud phone.

        This method first queries the available app list, optionally filters by version,
        then installs matching apps.

        API: POST /cloudphone/app/page (search) + POST /cloudphone/app/install (install)

        Args:
            phone_id: Cloud phone ID (str or int).
            app_name: App name to search for (optional).
            version_name: Specific version to install (optional, filters results).
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response from the last install operation, or empty dict if no app found.
        """
        app_list = []
        payload = {
            "page_num": 1,
            "page_size": 100,
            "app_name": app_name,
        }

        response = self._post("/cloudphone/app/page", payload=payload, timeout=timeout)
        if response.get('code', -1) == 0:
            data_res = response.get('data', {})
            # Handle both list and dict response formats
            if isinstance(data_res, list):
                raw_list = data_res
            elif isinstance(data_res, dict):
                raw_list = data_res.get('dataList', [])
            else:
                raw_list = []

            for app in raw_list:
                version_list = app.get('appVersionList', [])
                if version_name:
                    filtered_versions = [v for v in version_list if v.get('versionName') == version_name]
                    if not filtered_versions:
                        continue
                    app['appVersionList'] = filtered_versions
                app_list.append(app)

        res = {}
        # Install matching apps
        for app in app_list:
            package_name = app.get('packageName')
            for ver in app.get('appVersionList', []):
                version_code = ver.get('versionCode')
                if version_code is not None:
                    version_code = int(version_code)
                    print(f"[INFO] Installing {app.get('appName')} "
                          f"(package: {package_name}, version: {ver.get('versionName')}, "
                          f"versionCode: {version_code})...")
                    payload = {
                        "id": phone_id,
                        "packageName": package_name,
                        "versionCode": version_code
                    }
                    res = self._post("/cloudphone/app/install", payload=payload, timeout=timeout)
                    print(f"[INFO] Install result: {res}")
        return res

    def install_app(self, phone_id, package_name: str, version_code: int, timeout=10):
        """
        Install a specific app on a cloud phone by package name and version code.

        API: POST /cloudphone/app/install
        Docs: https://guide.morelogin.com/api-reference/cloud-phone/open-api/apps/paths/~1cloudphone~1app~1install/post

        Args:
            phone_id: Cloud phone ID (str or int).
            package_name: App package name (e.g., "com.zhiliaoapp.musically").
            version_code: App version code (integer).
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response.
        """
        payload = {
            "id": phone_id,
            "packageName": package_name,
            "versionCode": version_code
        }
        return self._post("/cloudphone/app/install", payload=payload, timeout=timeout)

    def uninstall_app(self, phone_id, package_name: str, timeout=10):
        """
        Uninstall an app from a cloud phone.

        API: POST /cloudphone/app/uninstall
        Docs: https://guide.morelogin.com/api-reference/cloud-phone/open-api/apps/paths/~1cloudphone~1app~1uninstall/post

        Args:
            phone_id: Cloud phone ID (str or int).
            package_name: App package name to uninstall.
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response.
        """
        return self._post("/cloudphone/app/uninstall",
                          payload={"id": phone_id, "packageName": package_name}, timeout=timeout)

    def start_app(self, phone_id, package_name: str, timeout=10):
        """
        Launch an installed app on the cloud phone.

        API: POST /cloudphone/app/start

        Args:
            phone_id: Cloud phone ID (str or int).
            package_name: App package name to launch.
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response.
        """
        payload = {"id": phone_id, "packageName": package_name}
        return self._post("/cloudphone/app/start", payload=payload, timeout=timeout)

    def stop_app(self, phone_id, package_name: str, timeout=10):
        """
        Stop a running app on the cloud phone.

        API: POST /cloudphone/app/stop

        Args:
            phone_id: Cloud phone ID (str or int).
            package_name: App package name to stop.
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response.
        """
        payload = {"id": phone_id, "packageName": package_name}
        return self._post("/cloudphone/app/stop", payload=payload, timeout=timeout)

    def query_preinstalled_apps(self, package_name=None, timeout=10):
        """
        Query the list of team preinstalled apps.

        When the preinstall toggle is enabled, apps will be installed automatically
        after the device powers on — no manual install is needed.

        API: POST /cloudphone/team/app/page

        Args:
            package_name: Filter by specific package name (optional).
            timeout: Request timeout in seconds (default: 10).

        Returns:
            list: List of matching preinstalled app dicts.
            False: If no matching apps found.
        """
        data_list = []
        payload = {
            "page_num": 1,
            "page_size": 100
        }
        if package_name:
            payload['packageName'] = [package_name]

        response = self._post("/cloudphone/team/app/page", payload=payload, timeout=timeout)
        if response.get('code', -1) == 0:
            data_res = response.get('data', {})
            # Handle both list and dict response formats
            if isinstance(data_res, list):
                raw_list = data_res
            elif isinstance(data_res, dict):
                raw_list = data_res.get('dataList', [])
            else:
                raw_list = []
            if len(raw_list) == 0:
                return False
            data_list.append(raw_list[0])

        if len(data_list) == 0:
            return False

        return data_list

    def set_hide_accessibility(self, phone_id, package_name: str, timeout=10):
        """
        Hide accessibility service detection for a specific app.

        API: POST /cloudphone/app/setHideAccessibilityApp

        Behavior differs by Android version:
            - Android 13/14/15A/16: Set the package name of the accessibility app itself.
            - Android 12/15: Set the package name of the app you want to hide
              accessibility from (e.g., TikTok's package name to prevent it from
              detecting your accessibility service).

        Args:
            phone_id: Cloud phone ID (str or int).
            package_name: The package name to configure.
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response.
        """
        payload = {"ids": [phone_id], "packageName": [package_name]}
        return self._post("/cloudphone/app/setHideAccessibilityApp", payload=payload, timeout=timeout)

    def enable_root(self, phone_id, package_name: str, timeout=10):
        """
        Enable ROOT permission for a specific app on the cloud phone.

        API: POST /cloudphone/app/openRoot
        Docs: https://guide.morelogin.com/api-reference/cloud-phone/open-api/apps/appopenroot

        Args:
            phone_id: Cloud phone ID (str or int).
            package_name: App package name to grant ROOT access.
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response.
        """
        payload = {"id": phone_id, "packageNames": [package_name]}
        return self._post("/cloudphone/app/openRoot", payload=payload, timeout=timeout)

    # ======================== ADB & Touch ========================

    def execute_shell_command(self, phone_id, command: str, timeout=10):
        """
        Execute an ADB shell command on the cloud phone.

        API: POST /cloudphone/exeCommand
        Docs: https://guide.morelogin.com/api-reference/cloud-phone/open-api/adb/executeshellcommand

        Args:
            phone_id: Cloud phone ID (str or int).
            command: Shell command to execute (e.g., "wm size", "pm list packages").
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response with command output.
        """
        return self._post("/cloudphone/exeCommand",
                          payload={"id": phone_id, "command": command}, timeout=timeout)

    def get_screen_size(self, phone_id, timeout=10):
        """
        Get the physical screen resolution of the cloud phone.

        Executes "wm size" via ADB shell command.

        Args:
            phone_id: Cloud phone ID (str or int).
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response containing screen size info.
        """
        payload = {
            "id": phone_id,
            "command": "wm size"
        }
        return self._post("/cloudphone/exeCommand", payload=payload, timeout=timeout)

    def touch_click(self, phone_id, x: int, y: int, timeout=10):
        """
        Simulate a touch click at the specified coordinates.

        API: POST /cloudphone/touch/click
        Docs: https://guide.morelogin.com/api-reference/cloud-phone/open-api/touch/touchclick

        Args:
            phone_id: Cloud phone ID (str or int).
            x: X coordinate of the touch point.
            y: Y coordinate of the touch point.
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response.
        """
        payload = {
            "id": phone_id,
            "pos": [x, y]
        }
        return self._post("/cloudphone/touch/click", payload=payload, timeout=timeout)

    # ======================== Screenshot ========================

    def screenshot_base64(self, phone_id, timeout=10):
        """
        Take a screenshot and return it as a Base64-encoded string.

        API: POST /cloudphone/screenCapBase64

        Args:
            phone_id: Cloud phone ID (str or int).
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response containing Base64 screenshot data.
        """
        return self._post("/cloudphone/screenCapBase64", payload={"id": phone_id}, timeout=timeout)

    def screenshot_url(self, phone_id, timeout=10):
        """
        Take a screenshot and return a download URL.

        API: POST /cloudphone/screenCap

        Args:
            phone_id: Cloud phone ID (str or int).
            timeout: Request timeout in seconds (default: 10).

        Returns:
            dict: API response containing screenshot download URL.
        """
        return self._post("/cloudphone/screenCap", payload={"id": phone_id}, timeout=timeout)

    # ======================== File Transfer ========================

    def download_file(self, phone_id, file_path_on_phone: str, save_local_path: str, timeout=120):
        """
        Download a file from the cloud phone to the local machine.

        This is a two-step process:
            1. Request file download → get a download task ID.
            2. Poll download status until complete (status=20), then download via URL.

        API:
            - POST /cloudphone/download (initiate download)
            - POST /cloudphone/download/result (check download status)
        Docs: https://guide.morelogin.com/api-reference/cloud-phone/open-api/files

        Args:
            phone_id: Cloud phone ID (str or int).
            file_path_on_phone: Absolute file path on the cloud phone.
            save_local_path: Local path to save the downloaded file.
            timeout: Overall timeout in seconds (default: 120).

        Returns:
            tuple: (success: bool, response: dict)
                   - (True, status_response) on success.
                   - (False, error_info) on failure.
        """
        payload = {
            "id": phone_id,
            "filePath": file_path_on_phone
        }
        # Step 1: Request file download
        res = self._post("/cloudphone/download", payload=payload, timeout=timeout)
        if res.get('code', -1) != 0:
            print(f"[ERROR] Failed to request file download: {res}")
            return False, res

        down_id = res.get('data', {}).get('downId')
        if not down_id:
            print(f"[ERROR] Missing 'downId' in response: {res}")
            return False, res

        result_payload = {
            "id": phone_id,
            "downId": down_id
        }

        # Step 2: Poll download status until ready
        start_time = time.time()
        while time.time() - start_time < timeout:
            res_status = self._post("/cloudphone/download/result", payload=result_payload, timeout=timeout)
            if res_status.get('code', -1) == 0:
                data = res_status.get('data', {})
                status = data.get('status')
                if status == 20:  # Download ready
                    down_url = data.get('downUrl')
                    if down_url:
                        try:
                            file_data = requests.get(down_url, timeout=timeout).content
                            with open(save_local_path, 'wb') as f:
                                f.write(file_data)
                            print(f"[INFO] File downloaded and saved to: {save_local_path}")
                            return True, res_status
                        except Exception as e:
                            print(f"[ERROR] Failed to save file locally: {e}")
                            return False, {"error": str(e), "status_response": res_status}
                elif status in (30, 40):  # Download failed
                    print(f"[ERROR] Download task failed with status: {status}")
                    return False, res_status
            time.sleep(3)
        print("[ERROR] Timed out waiting for file download")
        return False, {"error": "Timeout waiting for download"}

    def upload_file(self, phone_id, file_path: str, upload_dest: str = None, timeout=120):
        """
        Upload a local file to the cloud phone.

        This is a three-step process:
            1. Get a presigned upload URL from the API.
            2. Upload the file to the presigned URL via HTTP PUT.
            3. Push the uploaded file to the cloud phone.

        API:
            - POST /cloudphone/uploadUrl (get presigned URL)
            - PUT {presigned_url} (upload file)
            - POST /cloudphone/uploadFile (push to device)

        Args:
            phone_id: Cloud phone ID (str or int).
            file_path: Local file path to upload.
            upload_dest: Destination path on the phone (default: "/Download").
            timeout: Request timeout in seconds (default: 120).

        Returns:
            tuple: (success: bool, response: dict)
                   - (True, push_response) on success.
                   - (False, error_info) on failure.
        """
        if not os.path.exists(file_path):
            print(f"[ERROR] Local file not found: {file_path}")
            return False, {"error": "Local file not found"}

        file_name = os.path.basename(file_path)
        payload = {
            "id": phone_id,
            "fileName": file_name
        }
        if upload_dest:
            payload["uploadDest"] = upload_dest

        # Step 1: Get presigned upload URL
        res = self._post("/cloudphone/uploadUrl", payload=payload, timeout=timeout)
        if res.get('code', -1) != 0:
            print(f"[ERROR] Failed to get presigned upload URL: {res}")
            return False, res

        data = res.get('data', {})
        presigned_url = data.get('presignedUrl') if isinstance(data, dict) else None
        file_url = data.get('url') if isinstance(data, dict) else None

        if not presigned_url:
            print(f"[ERROR] Missing 'presignedUrl' in response: {res}")
            return False, res

        # Step 2: Upload file via HTTP PUT
        try:
            with open(file_path, 'rb') as f:
                headers = {"Content-Type": "application/octet-stream"}
                put_res = requests.put(presigned_url, data=f, headers=headers, timeout=timeout)
                if put_res.status_code != 200:
                    print(f"[ERROR] PUT upload failed with status {put_res.status_code}: {put_res.text}")
                    return False, {"error": f"PUT failed with status {put_res.status_code}", "response": put_res.text}
                print("[INFO] File uploaded to presigned URL successfully")
        except Exception as e:
            print(f"[ERROR] PUT upload exception: {e}")
            return False, {"error": str(e)}

        # Step 3: Push the uploaded file to the cloud phone
        if not file_url:
            file_url = presigned_url.split('?')[0] if presigned_url else ""

        push_payload = {
            "id": phone_id,
            "url": file_url,
            "uploadDest": upload_dest if upload_dest else "/Download"
        }
        push_res = self._post("/cloudphone/uploadFile", payload=push_payload, timeout=timeout)
        if push_res.get('code', -1) == 0:
            print("[INFO] File pushed to cloud phone successfully")
            return True, push_res
        else:
            print(f"[ERROR] Failed to push file to cloud phone: {push_res}")
            return False, push_res

    def get_upload_presigned_url(self, phone_id, file_path: str, upload_dest: str = None, timeout=120):
        """
        Upload a local file and return the presigned URL (without pushing to device).

        This is useful when you need to handle the file push step separately.

        Steps:
            1. Get a presigned upload URL from the API.
            2. Upload the file to the presigned URL via HTTP PUT.

        Args:
            phone_id: Cloud phone ID (str or int).
            file_path: Local file path to upload.
            upload_dest: Destination path on the phone (optional).
            timeout: Request timeout in seconds (default: 120).

        Returns:
            str: The file URL after upload.
            tuple: (False, error_info) on failure.
        """
        if not os.path.exists(file_path):
            print(f"[ERROR] Local file not found: {file_path}")
            return False, {"error": "Local file not found"}

        file_name = os.path.basename(file_path)
        payload = {
            "id": phone_id,
            "fileName": file_name
        }
        if upload_dest:
            payload["uploadDest"] = upload_dest

        # Step 1: Get presigned upload URL
        res = self._post("/cloudphone/uploadUrl", payload=payload, timeout=timeout)
        if res.get('code', -1) != 0:
            print(f"[ERROR] Failed to get presigned upload URL: {res}")
            return False, res

        data = res.get('data', {})
        presigned_url = data.get('presignedUrl') if isinstance(data, dict) else None
        file_url = data.get('url') if isinstance(data, dict) else None

        if not presigned_url:
            print(f"[ERROR] Missing 'presignedUrl' in response: {res}")
            return False, res

        # Step 2: Upload file via HTTP PUT
        try:
            with open(file_path, 'rb') as f:
                headers = {"Content-Type": "application/octet-stream"}
                put_res = requests.put(presigned_url, data=f, headers=headers, timeout=timeout)
                if put_res.status_code != 200:
                    print(f"[ERROR] PUT upload failed with status {put_res.status_code}: {put_res.text}")
                    return False, {"error": f"PUT failed with status {put_res.status_code}", "response": put_res.text}
                print("[INFO] File uploaded to presigned URL successfully")
        except Exception as e:
            print(f"[ERROR] PUT upload exception: {e}")
            return False, {"error": str(e)}

        # Return the file URL (without pushing to device)
        if not file_url:
            file_url = presigned_url.split('?')[0] if presigned_url else ""

        return file_url


# ======================== Usage Example ========================

if __name__ == '__main__':
    # Initialize client with your app_id and api_key
    # Get these from: MoreLogin Client → Settings → API & MCP
    client = MoreLoginCloudPhone("YOUR_APP_ID", "YOUR_API_KEY")

    # 1. Get token (auto-managed, but you can call manually to verify)
    print("Token:", client.get_token())

    # 2. List all cloud phones
    # devices = client.list_devices(page_no=1, page_size=10)
    # print("Devices:", devices)

    # 3. Power on a device
    # result = client.power_on("PHONE_ID")
    # print("Power on:", result)

    # 4. Wait until device is ready
    # info = client.wait_until_ready("PHONE_ID", timeout_seconds=300)
    # print("Device ready:", info)

    # 5. Get device info
    # info = client.get_device_info("PHONE_ID")
    # print("Device info:", info)

    # 6. Query device info by Android ID
    # info = client.get_device_info_by_android_id("ANDROID_ID")
    # print("Device info:", info)

    # 7. Install an app
    # result = client.install_app("PHONE_ID", "com.zhiliaoapp.musically", 2024504030)
    # print("Install:", result)

    # 8. Take a screenshot
    # screenshot = client.screenshot_base64("PHONE_ID")
    # print("Screenshot:", screenshot)

    # 9. Execute ADB command
    # result = client.execute_shell_command("PHONE_ID", "pm list packages")
    # print("ADB:", result)

    # 10. Upload a file to the device
    # success, res = client.upload_file("PHONE_ID", "/path/to/local/file.apk", "/Download")
    # print("Upload:", success, res)

    # 11. Download a file from the device
    # success, res = client.download_file("PHONE_ID", "/sdcard/DCIM/photo.jpg", "./photo.jpg")
    # print("Download:", success, res)

    # 12. Query preinstalled apps
    # apps = client.query_preinstalled_apps("com.appdeveloproot.RootAccess")
    # print("Preinstalled apps:", apps)
