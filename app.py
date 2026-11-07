import json
import traceback
import base64

import requests
import uvicorn
from fastapi import FastAPI, Response, status
import dotenv
import os


dotenv.load_dotenv()

app = FastAPI()


@app.get("/{path:path}")
async def subscription(path: str, response: Response):
    # 1. get sub_id and preferably name
    sub_path = os.getenv("SUB_PATH")
    if sub_path is None:
        return []
    if sub_path.startswith("/"):
        sub_path = sub_path[1:]

    if not path.startswith(sub_path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return "not found"

    sub_id = path.replace(sub_path, "")
    name = os.getenv(f"subid_{sub_id}_suffix", "")

    # 2. get sub_urls
    subs_urls = []
    subs_urls_temp = os.getenv("SUB_URLS").split(",")
    for sub_url in subs_urls_temp:
        subs_urls.append(sub_url.replace("{{SUB_ID}}", sub_id))

    # 3. retrieve configs
    upload = 0
    download = 0
    subs_jsons = []

    for sub_url in subs_urls:
        try:
            response = requests.get(sub_url, timeout=10)

            if response.status_code != 200:
                continue

            userinfo = response.headers.get("Subscription-Userinfo")
            if userinfo:
                userinfo = userinfo.split(";")
                for i in userinfo:
                    if i.strip().startswith("upload"):
                        upload += int(i.split("=")[1])
                    if i.strip().startswith("download"):
                        download += int(i.split("=")[1])

            sub_json = json.loads(response.text)
            for config in sub_json:
                subs_jsons.append(config)
                subs_jsons[-1]["remarks"] = subs_jsons[-1]["remarks"] + name if name else subs_jsons[-1]["remarks"]
        except:
            traceback.print_exc()

    return Response(
        content=json.dumps(subs_jsons),
        media_type="text/plain",
        headers={
            "Profile-Title": f"base64:{base64.b64encode(os.getenv("SUB_NAME").encode()).decode()}",
            "Announce": f"base64:{base64.b64encode(os.getenv("SUB_DESC").encode()).decode()}",
            "Support-Url": os.getenv("SUB_SUPPORT_URL") or "",
            "Profile-Web-Page-Url": os.getenv("SUB_PAGE_URL") or "",
            "Profile-Update-Interval": "1",
            "Subscription-Userinfo": f"upload={upload}; download={download}; total=0; expire=0"
        }
    )


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
