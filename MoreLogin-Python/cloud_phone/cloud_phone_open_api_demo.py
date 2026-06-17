import time
import requests
from requests.adapters import HTTPAdapter


class MLG:
    """ 海外云机  注意文档是英文的可能意思会变味了哦  只用广域网https://api.morelogin.com"不用本地 """
    def __init__(self, app_id: str, api_key: str):
        self.APP_ID, self.API_KEY, self.HOST = app_id, api_key, "https://api.morelogin.com"
        self.__data = {}  # 存所东西使用

        self.__session = requests.Session()
        adapter = HTTPAdapter(pool_connections=50, pool_maxsize=500, max_retries=1)
        self.__session.mount('http://', adapter)
        self.__session.mount('https://', adapter)
        self.__session.trust_env = False
        self.__session.allow_redirects = False

    def get_token(self, timeout=10):
        """ 获取 token 请求必须的认证   app_id, api_key这两个参在你的客户端中API&MCP中获取哦 """
        __access_token = ""
        url = f"{self.HOST}/oauth2/token"
        payload = {"client_id": self.APP_ID, "client_secret": self.API_KEY, "grant_type": "client_credentials"}
        headers = {"Content-Type": "application/json"}
        try:
            data_json = self.__session.post(url, json=payload, headers=headers, timeout=timeout).json()
            if data_json.get("code") == 0:
                __access_token = data_json.get('data', {}).get('access_token')
        except Exception as e:
            print(f"获取TOKEN异常：{e}")
        return __access_token

    def _POST(self, url_path: str, payload: any, timeout=10):
        __data = {}  # 为了防报错统一标准字典类型
        try:
            # 自动获取token
            if "access_token" not in self.__data.keys():
                access_token = self.get_token(timeout)
                if not access_token:
                    print(f"没有取到access_token")
                    return __data
                self.__data['access_token'] = access_token

            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.__data['access_token']}"}

            __data = self.__session.post(f"{self.HOST}{url_path}", json=payload, headers=headers, timeout=timeout).json()
        except Exception as e:
            print(f"请求路径:{url_path},异常:{e}")
        return __data

    def 设备列表(self, page_no: int = 1, page_size: int = 1000, timeout=10):
        """
        查询账号下云手机列表。
        必填参数:
            page_no: 页码，从 1 开始
            page_size: 每页数量
        可选参数:  已取消这个以下 keyword bind_ip
            keyword: 关键字过滤（环境名/分组/标签等）
            bind_ip: 是否过滤绑定 IP 的环境
            use_local_api: True=本地接口 /api/cloudphone/page, False=Open接口 /cloudphone/page
            if keyword:
                payload["keyword"] = keyword
            if bind_ip is not None:
                payload["bindIp"] = bind_ip
        返回:
            Dict[str, Any]: 原始响应 JSON（包含 code/msg/data/requestId）

        原始返回：{
        'code': 0,
        'msg': None,
        'data': {
            'total': '1',
            'current': '1',
            'pages': '1',
            'dataList': [{
                'id': '1707393745023023',
                'envName': 'yhtytg',
                'groupId': '0',
                'skuId': '10010',
                'tagIds': None,
                'tagInfo': None,
                'groupInfo': None,
                'billingType': 2,
                'proxyId': '1707418446214729',
                'proxyStatus': 0,
                'proxy': {
                    'id': '1707418446214729',
                    'proxyName': 'socks5://z1.ipmart.io:9595',
                    'proxyIp': 'z1.ipmart.io',
                    'exportIp': '46.183.108.54',
                    'proxyPort': 9595,
                    'groupId': '0',
                    'proxyType': 2,
                    'proxyCatagoryType': 2,
                    'proxyCheckStatus': 0,
                    'proxyInfo': '{
                        "type":"socks5",
                        "username":"5Hj9Ks2Cv9He-res-US-sid-854585",
                        "password":"Xv2u76ZeYPia86V123ab"}',
                    'country': 'United States of America', 'countryCode': 'US', 'delFlag': 0, 'uniqueId': 11, 'proxyTypeCode': '', 'proxyRegionCode': '', 'proxyAreaCode': '', 'providerCode': '', 'regionKey': '', 'proxyStatus': 1, 'createDate': '2026-06-04 16:13:33', 'expiryTime': None, 'releaseTime': None, 'proxySub': None}, 'lastStartMemberId': '1707387314972592', 'lastStartMemberName': 'Super administrator', 'lastStartDate': '2026-06-05 17:37:49', 'lastConnectMemberId': '0', 'lastConnectMemberName': None, 'lastConnectDate': None, 'envStatus': 2, 'abnormalStatus': 0, 'envRemark': '', 'supportAdb': True, 'enableAdb': False, 'adbInfo': None, 'expireTime': '1783170388938', 'createMember': '1707387314972592', 'updateMember': '1707387314972592', 'updateDate': '2026-06-05 17:38:51', 'createDate': '2026-06-04 12:57:16', 'createMemberName': 'Super administrator', 'powerOnBillingStrategy': None}]}, 'requestId': '8f55eee89c9a4d9394ec28bedea8cedb'}
        """
        payload = {
            "pageNo": page_no,
            "pageSize": page_size,
        }
        return self._POST("/cloudphone/page", payload=payload, timeout=timeout)

    # 开机不用设置云手机代理
    def 手机开机(self, phone_id: int or str, extra_payload: dict = None, timeout=10):
        """
        云手机开机。
        必填参数:
            phone_id: 云手机 ID
        可选参数:
            extra_payload: 透传额外字段（例如开机指定代理）
                示例: {"proxyId": 123456789}
        正在启动的返回:{'code': 33324, 'msg': 'The current profile is running.', 'data': {'isConcurrency': False, 'billingType': 2, 'duration': '0'}, 'requestId': '71b8e10d14dd4552a46d56c35c13506c'}
        没有启动的返回:{'code': 0, 'msg': None, 'data': {'isConcurrency': False, 'billingType': 2, 'duration': '0'}, 'requestId': '8ea683f7342c439d9cff16dd79864be3'}
        执行后的参返回:{'code': 33324, 'msg': 'The current profile is running.', 'data': {'isConcurrency': False, 'billingType': 2, 'duration': '0'}, 'requestId': 'd664d4dead4a4d6196761da41afe16cb'}
        """
        payload = {"id": phone_id}
        if extra_payload:
            payload.update(extra_payload)
        return self._POST("/cloudphone/powerOn", payload=payload, timeout=timeout)

    def 手机关机(self, phone_id: int or str, timeout=10):
        """
        把手机关掉 不知道他关掉的目的有什么用还是他的新机API必须要关闭才可以???【问】，这个常规的业务功能，如果用不到就不进行关机
        执行开着的云机返回：{'code': 0, 'msg': None, 'data': None, 'requestId': '7f932a4c71154da194462a2a448d0073'}
        执行关着的云机返回：{'code': 33301, 'msg': 'The Cloud Phone has not been started up.', 'data': None, 'requestId': '780a3c89b4b04ae6a4d20ed0b9fd79bd'} 其实算成功
        """
        payload = {"id": phone_id}
        __data = self._POST("/cloudphone/powerOff", payload=payload, timeout=timeout)
        if __data.get('code', -1) == 0 or __data.get('code', -1) == 33301:  # 关闭成功或根本就没有开 表示是成功了的返回真
            # print(f"手机关机成功:{__data}")
            return True
        # print(f"手机关机失败:{__data}")

    def 一键新机(self, phone_id: int or str, timeout=10):
        """
        一键新机（重置为新机环境）。
        必填参数:
            phone_id: 云手机 ID
        可选参数: 【以下我不用 我只要随机新机就行了,请问我写的对不】 ？？？？？ 可以的，不传机型就是会随机进行分配

            brand: 品牌
            model_id: 机型 ID
            use_local_api: True=本地接口 /api/cloudphone/newMachine, False=Open接口 /cloudphone/newMachine
            extra_payload: 透传额外字段（如文档新增参数）
        开着机的执行返回:{'code': 0, 'msg': None, 'data': None, 'requestId': 'db94221f9f564e5893597055482c30fe'} 有问题一直在99% 等很久哦差不多10多分钟  ？？？？ 请问你使用的是哪款机型
        反复新机的执行返回:{'code': 33301, 'msg': 'The Cloud Phone has not been started up.', 'data': None, 'requestId': 'c8423df22b6a4c4ab9d15efa0276cb4b'}  >>> 只有开机成功的状态下才允许一键新机，就是状态值=4 情况下才行
        """
        payload = {"id": phone_id}
        return self._POST("/cloudphone/newMachine", payload=payload, timeout=timeout)

    def 手机状态(self, phone_id: int or str, timeout=10):
        """
        查询云手机详情与状态。  （ 轮询云手机状态，直到 envStatus=4（已开机）。）
        必填参数:
            phone_id: 云手机 ID
        开着机的返回:{'code': 0, 'msg': None, 'data': {'id': '1707393745023023', 'envName': 'yhtytg', 'groupId': '0', 'skuId': '10010', 'tagIds': [], 'billingType': 2, 'proxyStatus': 3, 'settings': {'automaticGeo': True, 'automaticLocation': True, 'automaticLanguage': True, 'longitude': None, 'latitude': None, 'altitude': None, 'country': '', 'timezone': '', 'language': ''}, 'device': {'server': None, 'countryName': 'US', 'rom': 45, 'wifiBssid': None, 'bluetoothMac': 'E8:4E:84:99:08:78', 'osVersion': 'Android 15', 'imei': '352630606740361', 'phoneNumber': '+16793506376'}, 'proxy': {'id': '1707418446214729', 'proxyName': 'socks5://z1.ipmart.io:9595', 'proxyIp': 'z1.ipmart.io', 'exportIp': '198.254.115.5', 'proxyPort': 9595, 'groupId': '0', 'proxyType': 2, 'proxyCatagoryType': 2, 'proxyCheckStatus': 0, 'proxyInfo': '{"type":"socks5","username":"5Hj9Ks2Cv9He-res-US-sid-854585","password":"Xv2u76ZeYPia86V123ab"}', 'country': 'United States of America', 'countryCode': 'US', 'delFlag': 0, 'uniqueId': 11, 'proxyTypeCode': '', 'proxyRegionCode': '', 'proxyAreaCode': '', 'providerCode': '', 'regionKey': '', 'proxyStatus': 1, 'createDate': '2026-06-04 16:13:33', 'expiryTime': None, 'releaseTime': None, 'proxySub': None}, 'lastStartMemberId': '1707387314972592', 'lastStartMemberName': None, 'lastStartDate': '2026-06-05 19:35:50', 'lastConnectMemberId': '1707387314972592', 'lastConnectMemberName': None, 'lastConnectDate': '2026-06-05 19:44:48', 'envStatus': 4, 'abnormalStatus': 0, 'expireTime': '1783170388938', 'envRemark': '', 'createMember': '1707387314972592', 'updateMember': '1707387314972592', 'updateDate': '2026-06-05 19:47:18', 'createDate': '2026-06-04 12:57:16', 'createMemberName': None, 'powerOnBillingStrategy': None}, 'requestId': '273e03a1018546c5961faf16584b10eb'}
        关着机的返回:{'code': 0, 'msg': None, 'data': {'id': '1707393745023023', 'envName': 'yhtytg', 'groupId': '0', 'skuId': '10010', 'tagIds': [], 'billingType': 2, 'proxyStatus': 0, 'settings': {'automaticGeo': True, 'automaticLocation': True, 'automaticLanguage': True, 'longitude': None, 'latitude': None, 'altitude': None, 'country': '', 'timezone': '', 'language': ''}, 'device': {'server': None, 'countryName': 'US', 'rom': 45, 'wifiBssid': None, 'bluetoothMac': 'E8:4E:84:99:08:78', 'osVersion': 'Android 15', 'imei': '352630606740361', 'phoneNumber': '+16793506376'}, 'proxy': {'id': '1707418446214729', 'proxyName': 'socks5://z1.ipmart.io:9595', 'proxyIp': 'z1.ipmart.io', 'exportIp': '198.254.115.5', 'proxyPort': 9595, 'groupId': '0', 'proxyType': 2, 'proxyCatagoryType': 2, 'proxyCheckStatus': 0, 'proxyInfo': '{"type":"socks5","username":"5Hj9Ks2Cv9He-res-US-sid-854585","password":"Xv2u76ZeYPia86V123ab"}', 'country': 'United States of America', 'countryCode': 'US', 'delFlag': 0, 'uniqueId': 11, 'proxyTypeCode': '', 'proxyRegionCode': '', 'proxyAreaCode': '', 'providerCode': '', 'regionKey': '', 'proxyStatus': 1, 'createDate': '2026-06-04 16:13:33', 'expiryTime': None, 'releaseTime': None, 'proxySub': None}, 'lastStartMemberId': '1707387314972592', 'lastStartMemberName': None, 'lastStartDate': '2026-06-05 19:35:50', 'lastConnectMemberId': '0', 'lastConnectMemberName': None, 'lastConnectDate': None, 'envStatus': 2, 'abnormalStatus': 0, 'expireTime': '1783170388938', 'envRemark': '', 'createMember': '1707387314972592', 'updateMember': '1707387314972592', 'updateDate': '2026-06-05 19:48:16', 'createDate': '2026-06-04 12:57:16', 'createMemberName': None, 'powerOnBillingStrategy': None}, 'requestId': '747806ee6711477cbba3f76999b8fbd7'}
        新机后的返回:{'code': 0, 'msg': None, 'data': {'id': '1707393745023023', 'envName': 'yhtytg', 'groupId': '0', 'skuId': '10010', 'tagIds': [], 'billingType': 2, 'proxyStatus': 3, 'settings': {'automaticGeo': True, 'automaticLocation': True, 'automaticLanguage': True, 'longitude': None, 'latitude': None, 'altitude': None, 'country': '', 'timezone': '', 'language': ''}, 'device': {'server': None, 'countryName': 'US', 'rom': 45, 'wifiBssid': None, 'bluetoothMac': '38:2D:E8:B9:1F:6A', 'osVersion': 'Android 15', 'imei': '869499070759018', 'phoneNumber': '+19806298919'}, 'proxy': {'id': '1707418446214729', 'proxyName': 'socks5://z1.ipmart.io:9595', 'proxyIp': 'z1.ipmart.io', 'exportIp': '73.77.230.179', 'proxyPort': 9595, 'groupId': '0', 'proxyType': 2, 'proxyCatagoryType': 2, 'proxyCheckStatus': 0, 'proxyInfo': '{"type":"socks5","username":"5Hj9Ks2Cv9He-res-US-sid-854585","password":"Xv2u76ZeYPia86V123ab"}', 'country': 'United States of America', 'countryCode': 'US', 'delFlag': 0, 'uniqueId': 11, 'proxyTypeCode': '', 'proxyRegionCode': '', 'proxyAreaCode': '', 'providerCode': '', 'regionKey': '', 'proxyStatus': 1, 'createDate': '2026-06-04 16:13:33', 'expiryTime': None, 'releaseTime': None, 'proxySub': None}, 'lastStartMemberId': '1707387314972592', 'lastStartMemberName': None, 'lastStartDate': '2026-06-05 19:49:47', 'lastConnectMemberId': '1707387314972592', 'lastConnectMemberName': None, 'lastConnectDate': '2026-06-05 19:51:29', 'envStatus': 7, 'abnormalStatus': 0, 'expireTime': '1783170388938', 'envRemark': '', 'createMember': '1707387314972592', 'updateMember': '1707387314972592', 'updateDate': '2026-06-05 19:51:29', 'createDate': '2026-06-04 12:57:16', 'createMemberName': None, 'powerOnBillingStrategy': None}, 'requestId': 'db8e2a5277b64996852512eb1b5c9d38'}

        """
        return self._POST("/cloudphone/info", payload={"id": phone_id}, timeout=timeout)

    # 试了很多次只是有时执行成功了 但实际是没有开机的 发现
    def 是否开机(self, phone_id: int or str, tms=300, q=None, timeout=10):
        """  tms=开机超时 默认为5分钟 成功则返回（手机状态 函数的原始字典） """
        _tm = int(time.time())
        while True:
            info_data = self.手机状态(phone_id, timeout)
            env_status = info_data.get('data', {}).get('envStatus')
            if env_status == 4:
                if q:
                    q(f'开机成功OK')
                else:
                    print(f'开机成功OK')
                time.sleep(1)
                return info_data
            else:
                if q:
                    q(f"等待开机，用时{int(time.time()) - _tm}秒")
                else:
                    print(f"等待开机，用时{int(time.time()) - _tm}秒")
            if int(time.time()) - _tm >= tms:
                if q:
                    q(f'是否开机,超时:{tms}秒失败')
                else:
                    print(f'是否开机,超时:{tms}秒失败')
                time.sleep(1)
                return False
            time.sleep(5)

    def 应用列表(self, phone_id: int or str, timeout=10):
        """
        查询云手机已安装应用列表。
        原始返回：{'code': 0, 'msg': None, 'data': [], 'requestId': 'c9cf6b82c22143d7868324323a6e95a9'}
        原始返回：{'code': 0, 'msg': None, 'data': [{'appName': 'TikTok', 'appIcon': 'https://get.morelogin.com/prod/cloud_phone/app/62bc7373d51f3_icon.png', 'packageName': 'com.zhiliaoapp.musically', 'versionCode': '2024504030', 'versionName': '45.4.3'}], 'requestId': 'd28279812a0e43c1a0db49d743fcd44b'}

        预装应用 没有等待回调成本时不记录安装记录，需要确认？
        """
        __data_list = []
        _data = self._POST("/cloudphone/app/installedList", payload={"id": phone_id}, timeout=timeout)
        if _data.get('code', -1) == 0:
            __data_list = _data.get('data', [])
        return __data_list

    def 安装应用(self, phone_id: int or str, app_name=None, version_name=None, timeout=10):
        """
        查询云手机可安装应用列表。支持按版本号过滤。
        """
        __data_list = []
        payload = {
            "page_num": 1,
            "page_size": 100,
            "app_name": app_name,
        }

        _data = self._POST("/cloudphone/app/page", payload=payload, timeout=timeout)
        if _data.get('code', -1) == 0:
            data_res = _data.get('data', {})
            # 兼容处理：API 可能直接返回 list，也可能返回 dict 并包含 dataList
            if isinstance(data_res, list):
                raw_list = data_res
            elif isinstance(data_res, dict):
                raw_list = data_res.get('dataList', [])
            else:
                raw_list = []

            for app in raw_list:
                # 过滤版本号
                version_list = app.get('appVersionList', [])
                if version_name:
                    filtered_versions = [v for v in version_list if v.get('versionName') == version_name]
                    if not filtered_versions:
                        continue
                    # 更新应用的版本列表为过滤后的版本
                    app['appVersionList'] = filtered_versions
                __data_list.append(app)

        res = {}
        # 2. 进行应用安装
        for app in __data_list:
            package_name = app.get('packageName')
            for ver in app.get('appVersionList', []):
                version_code = ver.get('versionCode')
                if version_code is not None:
                    version_code = int(version_code)
                    print(
                        f"正在安装 {app.get('appName')} (包名: {package_name}, 版本名: {ver.get('versionName')}, 版本号: {version_code})...")
                    payload = {
                        "id": phone_id,
                        "packageName": package_name,
                        "versionCode": version_code
                    }
                    res = self._POST("/cloudphone/app/install", payload=payload, timeout=timeout)
                    print(f"安装结果：", res)
        return res

    def 查询预装应用(self, package_name=None, timeout=10):
        """
        查询云手机可安装应用列表。支持按版本号过滤。
        """
        __data_list = []
        payload = {
            "page_num": 1,
            "page_size": 100
        }
        if package_name:
            payload['packageName'] = [package_name]

        _data = self._POST("/cloudphone/team/app/page", payload=payload, timeout=timeout)
        if _data.get('code', -1) == 0:
            data_res = _data.get('data', {})
            # 兼容处理：API 可能直接返回 list，也可能返回 dict 并包含 dataList
            if isinstance(data_res, list):
                raw_list = data_res
            elif isinstance(data_res, dict):
                raw_list = data_res.get('dataList', [])
            else:
                raw_list = []
            if len(raw_list) == 0:
                return False
            __data_list.append(raw_list[0])

        if len(__data_list) == 0:
            return False

        return __data_list


    # ？？？？？？？？
    # 接口：https://guide.morelogin.com/api-reference/cloud-phone/local-api/apps/paths/~1api~1cloudphone~1app~1install/post
    def 实际安装应用(self, phone_id: int or str, packageName: str, versionCode: int, timeout=10):
        """ 安装应用到云手机 """
        payload = {
            "id": phone_id,
            "packageName": packageName,
            "versionCode": versionCode
        }
        return self._POST("/cloudphone/app/install", payload=payload, timeout=timeout)

    # 接口地址：https://guide.morelogin.com/api-reference/cloud-phone/open-api/apps/paths/~1cloudphone~1app~1uninstall/post
    def 卸载应用(self, phone_id: int or str, packageName: str, timeout=10):
        """ 是多少   """
        return self._POST("/cloudphone/app/uninstall", payload={"id": phone_id, "packageName": packageName}, timeout=timeout)

    # https://guide.morelogin.com/api-reference/cloud-phone/open-api/adb/executeshellcommand
    def ADB命令(self, phone_id: int or str, command: str, timeout=10):
        """ 是多少      """
        return self._POST("/cloudphone/exeCommand", payload={"id": phone_id, "command": command},
                          timeout=timeout)

    def 删除代理(self, proxy_id: int or str, timeout=10):
        return self._POST("/proxyInfo/delete", payload=[proxy_id],
                          timeout=timeout)


    # 接口：
    # 第一步请求文件下载：https://guide.morelogin.com/api-reference/cloud-phone/open-api/files/paths/~1cloudphone~1download/post
    # 第二步查询文件下载状态：https://guide.morelogin.com/api-reference/cloud-phone/open-api/files/paths/~1cloudphone~1download~1result/post
    # data.status = 20说明下载成功可以使用 data.downUrl进行文件下载
    def 下载文件到电脑(self, phone_id: int or str, file_path_on_phone: str, save_local_path: str, timeout=120):
        """
        把手机中的文件拉取到电脑。
        第一步请求文件下载：POST /cloudphone/download
        第二步查询文件下载状态：POST /cloudphone/download/result
        data.status = 20说明下载成功可以使用 data.downUrl进行文件下载
        """
        payload = {
            "id": phone_id,
            "filePath": file_path_on_phone
        }
        # 1. 第一步请求文件下载
        res = self._POST("/cloudphone/download", payload=payload, timeout=timeout)
        if res.get('code', -1) != 0:
            print(f"请求下载文件失败: {res}")
            return False, res

        down_id = res.get('data', {}).get('downId')
        if not down_id:
            print(f"未能在返回数据中获取到 downId: {res}")
            return False, res

        result_payload = {
            "id": phone_id,
            "downId": down_id
        }

        # 2. 第二步查询文件下载状态并进行文件下载 (轮询)
        start_time = time.time()
        while time.time() - start_time < timeout:
            res_status = self._POST("/cloudphone/download/result", payload=result_payload, timeout=timeout)
            if res_status.get('code', -1) == 0:
                data = res_status.get('data', {})
                status = data.get('status')
                if status == 20:  # 20 说明下载成功
                    down_url = data.get('downUrl')
                    if down_url:
                        # 下载文件到本地
                        try:
                            file_data = requests.get(down_url, timeout=timeout).content
                            with open(save_local_path, 'wb') as f:
                                f.write(file_data)
                            print(f"下载文件成功并保存至: {save_local_path}")
                            return True, res_status
                        except Exception as e:
                            print(f"保存本地文件异常: {e}")
                            return False, {"error": str(e), "status_response": res_status}
                elif status in [30, 40]:  # 30或40为失败状态
                    print(f"云机下载文件任务失败，状态码: {status}")
                    return False, res_status
            time.sleep(3)
        print("查询文件下载状态超时")
        return False, {"error": "Timeout waiting for download"}


    def 上传文件到手机(self, phone_id: int or str, file_path: str, upload_dest: str = None, timeout=120):
        """
        把电脑的文件上传给手机（第一步通过接口获取预上传链接，第二步通过Put请求上传文件，第三步调用接口推送到手机）。
        """
        import os
        if not os.path.exists(file_path):
            print(f"本地文件不存在: {file_path}")
            return False, {"error": "Local file not found"}

        file_name = os.path.basename(file_path)
        payload = {
            "id": phone_id,
            "fileName": file_name
        }
        if upload_dest:
            payload["uploadDest"] = upload_dest

        # 1. 第一步获取预上传链接
        res = self._POST("/cloudphone/uploadUrl", payload=payload, timeout=timeout)
        if res.get('code', -1) != 0:
            print(f"获取预上传链接失败: {res}")
            return False, res

        data = res.get('data', {})
        presigned_url = data.get('presignedUrl') if isinstance(data, dict) else None
        file_url = data.get('url') if isinstance(data, dict) else None # 对应推送到手机所需的 file_url

        if not presigned_url:
            print(f"未能在返回参数中找到 presignedUrl: {res}")
            return False, res

        # 2. 第二步通过 Put 请求上传文件到 presignedUrl
        try:
            with open(file_path, 'rb') as f:
                headers = {"Content-Type": "application/octet-stream"}
                put_res = requests.put(presigned_url, data=f, headers=headers, timeout=timeout)
                if put_res.status_code != 200:
                    print(f"PUT 上传文件失败, 状态码: {put_res.status_code}, 详情: {put_res.text}")
                    return False, {"error": f"PUT failed with status {put_res.status_code}", "response": put_res.text}
                print("本地文件上传至预上传链接成功")
        except Exception as e:
            print(f"PUT 请求上传异常: {e}")
            return False, {"error": str(e)}

        # 3. 第三步将文件推送到手机中
        if not file_url:
            file_url = presigned_url.split('?')[0] if presigned_url else ""

        push_payload = {
            "id": phone_id,
            "url": file_url,
            "uploadDest": upload_dest if upload_dest else "/Download"
        }
        push_res = self._POST("/cloudphone/uploadFile", payload=push_payload, timeout=timeout)
        if push_res.get('code', -1) == 0:
            print("文件推送到云手机命令发送成功")
            return True, push_res
        else:
            print(f"推送到云手机失败: {push_res}")
            return False, push_res

    #https://guide.morelogin.com/api-reference/cloud-phone/open-api/cloud-phone-management/setproxy
    def 设置代理(self, phone_id: int or str, proxy_type: int, sk5_host: str, sk5_port: int , sk5_user: str, sk5_pwd: str, timeout=20):
        """  是多少      """
        # proxyProvider 0: http, 1: https, 2: socks5
        payload = {
           "ids": [phone_id],
           "proxy": {
               "proxyProvider": proxy_type,
               "proxyIp": sk5_host,
               "proxyPort": sk5_port,
               "username": sk5_user,
               "password": sk5_pwd
           }
        }
        return self._POST("/cloudphone/setProxy", payload=payload, timeout=timeout)

    def 启动应用(self, phone_id: int or str, bid: str, timeout=10):
        """
        启动指定包名的应用。
        返回:
        """
        payload = {"id": phone_id, "packageName": bid}
        return self._POST("/cloudphone/app/start", payload=payload, timeout=timeout)

    def 关闭应用(self, phone_id: int or str, bid: str, timeout=10):
        """
        关闭指定包名的应用。
        返回:
        """
        payload = {"id": phone_id, "packageName": bid}
        return self._POST("/cloudphone/app/stop", payload=payload, timeout=timeout)

    def 隐无障碍(self, phone_id: int or str, bid: str, timeout=10):

        payload = {"ids": [phone_id], "packageName": [bid]}
        # 隐藏无障碍
        # 1、安卓13、安卓14、安卓15A、安卓16 设置应用本身的包名
        # 2、安卓12、安卓15 设置的是不让检测的应用包名 比如应用是 A开启了无障碍， 不想让TikTok检测出 A应用的无障碍模式，把TikTok的包名设置上
        return self._POST("/cloudphone/app/setHideAccessibilityApp", payload=payload, timeout=timeout)


    # https://guide.morelogin.com/api-reference/cloud-phone/open-api/apps/appopenroot
    def 设置ROOT(self, phone_id: int or str, bid: str, timeout=10):
        """
        设置指定 APP 的 ROOT 权限（占位方法，待最终文档）。
        必填参数:
            ids: 云手机 ID 列表  我只要单个
            package_name: 应用包名
            enable_root: True 开启 / False 关闭
        可选参数:
            endpoint_path: 接口路径（请替换成最终文档路径）
            use_local_api: True=请求本地地址, False=请求Open地址
        返回:
        """
        payload = {"id": phone_id, "packageNames": [bid]}
        return self._POST("/cloudphone/app/openRoot", payload=payload, timeout=timeout)

    def 上传文件到手机(self, phone_id: int or str, file_path: str, upload_dest: str = None, timeout=120):
        """
        把电脑的文件上传给手机（第一步通过接口获取预上传链接，第二步通过Put请求上传文件，第三步调用接口推送到手机）。
        """
        import os
        if not os.path.exists(file_path):
            print(f"本地文件不存在: {file_path}")
            return False, {"error": "Local file not found"}

        file_name = os.path.basename(file_path)
        payload = {
            "id": phone_id,
            "fileName": file_name
        }
        if upload_dest:
            payload["uploadDest"] = upload_dest

        # 1. 第一步获取预上传链接
        res = self._POST("/cloudphone/uploadUrl", payload=payload, timeout=timeout)
        if res.get('code', -1) != 0:
            print(f"获取预上传链接失败: {res}")
            return False, res

        data = res.get('data', {})
        presigned_url = data.get('presignedUrl') if isinstance(data, dict) else None
        file_url = data.get('url') if isinstance(data, dict) else None # 对应推送到手机所需的 file_url

        if not presigned_url:
            print(f"未能在返回参数中找到 presignedUrl: {res}")
            return False, res

        # 2. 第二步通过 Put 请求上传文件到 presignedUrl
        try:
            with open(file_path, 'rb') as f:
                headers = {"Content-Type": "application/octet-stream"}
                put_res = requests.put(presigned_url, data=f, headers=headers, timeout=timeout)
                if put_res.status_code != 200:
                    print(f"PUT 上传文件失败, 状态码: {put_res.status_code}, 详情: {put_res.text}")
                    return False, {"error": f"PUT failed with status {put_res.status_code}", "response": put_res.text}
                print("本地文件上传至预上传链接成功")
        except Exception as e:
            print(f"PUT 请求上传异常: {e}")
            return False, {"error": str(e)}

        # 3. 第三步将文件推送到手机中
        if not file_url:
            file_url = presigned_url.split('?')[0] if presigned_url else ""

        return file_url

    def 通过AndroidId查手机手机信息(self, android_id: int or str, timeout=10):
        """
        通过androidId查询云手机详情
        必填参数:
            phone_id: 云手机 ID
        """
        return self._POST("/cloudphone/queryByAndroidId", payload={"androidId": android_id}, timeout=timeout)

    def 截图Base64(self, phone_id: int or str, timeout=10):
        """
        通过云手机ID截图
        必填参数:
            phone_id: 云手机 ID
        """
        return self._POST("/cloudphone/screenCapBase64", payload={"id": phone_id}, timeout=timeout)

    def 获取图片(self, phone_id: int or str, timeout=10):
        return self._POST("/cloudphone/screenCap", payload={"id": phone_id}, timeout=timeout)

    # 接口地址：https://guide.morelogin.com/zh/api-reference/cloud-phone/open-api/adb/executeshellcommand
    def PhysicalSize(self, phone_id: int or str, timeout=10):
        # x,y 坐标请根据实际进行传输
        payload = {
            "id": phone_id,
            "command": "wm size"
        }
        return self._POST("/cloudphone/exeCommand", payload=payload, timeout=timeout)

    # 接口地址：https://guide.morelogin.com/zh/api-reference/cloud-phone/open-api/touch/touchclick
    def ADB点击(self, phone_id: int or str, x: int, y: int, timeout=10):
        # x,y 坐标请根据实际进行传输
        payload = {
            "id": phone_id,
            "pos": [x, y]
        }
        return self._POST("/cloudphone/touch/click", payload=payload, timeout=timeout)

if __name__ == '__main__':
    """ MLG云机 """
    m = MLG("1707784436203449", "938bad7ca6824198a70dba77c29d27ac")
    print(f"token：", m.get_token())

    print(f"查询预装应用：", m.查询预装应用("com.appdeveloproot.RootAccess"))  # 预装应用安装 开关 打开时开机成功后会自动安装，不需要手动触发安装
    print(f"通过AndroidId查询云手机信息：", m.通过AndroidId查手机手机信息("4294c18056cc72bd"))

    print(f"截图Base64：", m.截图Base64("1707214184730167"))

    # 预装应用安装 开关 打开时开机成功后会自动安装，不需要手动触发安装
    # 查询云手机列表和云手机信息也增加了 androidId 字段返回
    # 截图接口 测试验证还有问题，需要明天才能提供







