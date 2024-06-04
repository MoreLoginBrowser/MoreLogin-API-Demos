# pip install requests playwright pycryptodome Crypto
from base_morelogin.base_func import requestHeader, postRequest

import sys
import asyncio
from playwright.async_api import async_playwright, Playwright     # async call 
import traceback

# From profile list page, click on the API button, and copy API ID and API Key to below.
APPID = '123456'
SECRETKEY = 'abcdef'
BASEURL = 'http://127.0.0.1:40000'

async def main():
    async with async_playwright() as playwright:
        await run(playwright)

async def run(playwright: Playwright):
    try:
        env_id = '1797528993729015808' # browser profile id, please check API-demo: list_browser_profiles.py 
        cdp_url = await startEnv(env_id, APPID, SECRETKEY, BASEURL)

        await operationEnv(cdp_url, playwright)

        # wait 10 second
        await asyncio.sleep(10)

        # try close env
        await stopEnv(env_id, APPID, SECRETKEY, BASEURL)

    except:
        error_message = traceback.format_exc()
        print('run-error: ' + error_message)

# start a browser profile, and return cdp-url
async def startEnv(env_id, appId, secretKey, baseUrl):
    requestPath = baseUrl + '/api/env/start'  
    data = { 
        'id': env_id 
    }
    headers = requestHeader(appId, secretKey)
    response = postRequest(requestPath, data, headers).json()

    if response['code'] != 0:
        print(response['msg'])
        print('please check env_id')
        sys.exit()

    port = response['data']['debugPort']
    cdp_url = 'http://127.0.0.1:' + port
    return  cdp_url

# open page and operation
async def operationEnv(cdp_url, playwright):
        browser = await playwright.chromium.connect_over_cdp( cdp_url )
        default_context = browser.contexts[0]
        
        # try open page
        page1 = await default_context.new_page()
        await page1.goto('https://www.speedtest.net/')

        page2 = await default_context.new_page()
        await page2.goto('https://ipinfo.io')

        # try close and clear resource
        # await page1.close()
        # await page2.close()

# close a browser profile
async def stopEnv(env_id, appId, secretKey, baseUrl):
    requestPath = '/api/env/close'   
    data = { 
        'id': env_id 
    }
    headers = requestHeader(appId, secretKey)
    response = postRequest(baseUrl + requestPath, data, headers).json()
    if response['code'] == -1:
        return False
    return True      


if __name__ == '__main__':
    asyncio.run(main())