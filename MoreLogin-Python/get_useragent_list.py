"""
Description: 
Queries the available browser kernel versions.

Documentation:
https://docs.morelogin.com/l/en/interface-documentation/browser-profile#9_get_a_list_of_browser_kernel_versions
"""

# pip install requests pycryptodome Crypto
from base_morelogin.base_func import requestHeader, getRequest

import sys
import asyncio
import traceback

# From profile list page, click on the API button, and copy API ID and API Key to below.
APPID = '123456'
SECRETKEY = 'abcdef'
BASEURL = 'http://127.0.0.1:40000'

async def main():
    try:
        data = await getKernelList(APPID, SECRETKEY, BASEURL)
        if len(data) > 0:
            for ua in data:
                if ua['browserType'] == 1:
                    print('chromium version support:', ua['versions'])
                if ua['browserType'] == 2:
                    print('firefox version support:', ua['versions'])
        else:
            print('no ua data found, please call service')

    except:
        error_message = traceback.format_exc()
        print('run-error: ' + error_message)

async def getKernelList(appId, secretKey, baseUrl):
    requestPath = baseUrl + '/api/env/advanced/ua/versions'
    headers = requestHeader(appId, secretKey)
    response = getRequest(requestPath, headers).json()

    if response['code'] != 0:
        print('error:'+ requestPath + '\r\n' + response['msg'])
        sys.exit()

    #print(response)
    return response['data']

if __name__ == '__main__':
    asyncio.run(main())