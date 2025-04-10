import json
from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("MoreLoginAPI")


@mcp.tool()
async def start_profile(env_id=None, unique_id=None) -> str:
    """start a browser profile, need to provide env_id or unique_id.

    Args:
        env_id: profile id
        unique_id: profile order number
    """
    data = {"envId": env_id, "uniqueId": unique_id}
    print(f"env_id: {env_id}, unique_id: {unique_id}")
    if not env_id and not unique_id:
        return "env_id or unique_id must be provided"
    response = requests.post("http://localhost:40000/api/env/start", json=data).json()

    if response["code"] != 0:
        return json.dumps(response, indent=4)
        # return f"start failed. code: {response['code']}, error: {response['msg']}, request_id: {response.get('requestId')}"
    return response["data"]


if __name__ == "__main__":
    mcp.run(transport="stdio")
