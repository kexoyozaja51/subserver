import traceback
import base64
from urllib.parse import parse_qs, unquote, urlparse

import requests
import uvicorn
from fastapi import FastAPI, Response, status
import dotenv
import os


dotenv.load_dotenv()

app = FastAPI()


def convert_http2_to_naive(line: str) -> str:
    if not line.startswith("http2://"):
        return line

    try:
        parsed = urlparse(line)

        encoded = parsed.netloc
        decoded = base64.b64decode(
            encoded + "=" * (-len(encoded) % 4)
        ).decode()

        params = parse_qs(parsed.query)
        peer = params.get("peer", [""])[0]
        fragment = unquote(parsed.fragment)

        result = f"naive+https://{decoded}"

        result += "?uot=1&security=tls"

        if peer:
            result += f"&sni={peer}"

        if fragment:
            result += f"#{fragment}"

        return result

    except Exception:
        return line

@app.get("/{path:path}")
async def subscription(path: str, response: Response):
    # 1. get sub_id
    sub_path = os.getenv("SUB_PATH")
    if sub_path.startswith("/"):
        sub_path = sub_path[1:]

    if not path.startswith(sub_path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return "not found"

    sub_id = path.replace(sub_path, "")
    
    # 2. get sub_urls
    subs_urls = []
    subs_urls_temp = os.getenv("SUB_URLS").split(",")
    for sub_url in subs_urls_temp:
        subs_urls.append(sub_url.replace("{{SUB_ID}}", sub_id))

    # 3. retrieve configs
    upload = 0
    download = 0
    subs_configs = []
    
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
            
            for line in response.text.splitlines():
                line = line.strip()

                if line.startswith("naive+https://"):
                    continue

                if line:
                    line = convert_http2_to_naive(line)
                
                name = os.getenv(f"subid_{sub_id}_suffix", "")
                line = f"{line}{name}" if name else line
                subs_configs.append(line)
        except:
            traceback.print_exc()

    return Response(
        content="\n".join(subs_configs),
        media_type="text/plain", 
        headers= {
            "Profile-Title": f"base64:{base64.b64encode(os.getenv("SUB_NAME").encode()).decode()}",
            "Announce": f"base64:{base64.b64encode(os.getenv("SUB_DESC").encode()).decode()}",
            "Support-Url": os.getenv("SUB_SUPPORT_URL"),
            "Profile-Web-Page-Url": os.getenv("SUB_PAGE_URL"),
            "Profile-Update-Interval": "1",
            "Subscription-Userinfo": (f"upload={upload}; download={download}; total=0; expire=0")
        }
    )

    """# 3. retrieve jsons
    sub_jsons = []

    for sub_url in sub_urls:
        try:
            response = requests.get(sub_url, timeout=10)

            if response.status_code != 200:
                continue

            sub_json = json.loads(response.text)

            if isinstance(sub_json, dict):
                sub_jsons.extend([
                    {**sub_json, "outbounds": [outbound]} 
                    for outbound in sub_json["outbounds"]
                ])
            else:
                sub_jsons.extend(sub_json)

            ""if isinstance(sub_json, list):
                sub_jsons.extend(sub_json)
            else:
                sub_jsons.append(sub_json)""

        except Exception:
            traceback.print_exc()

    # 4. convert relevant jsons to configs

    sub_configs = []

    for sub_json in sub_jsons:
        print("===")
        outbound_type = sub_json["outbounds"][0].get("type", sub_json["outbounds"][0].get("protocol", None))
        print("outbound_type", outbound_type)
        print(sub_json)

        match outbound_type:
            case "vless":
                sub_configs.append(convert_vless(sub_json))

        ""if outbound_type in ("naive", "vless"):
            temp.append(sub_json)
            print("ADDED")
            #outbound_json = copy.deepcopy(template_json)
            #outbound_json["outbounds"] = [sub_json["outbounds"][0]]
            #print(outbound_json)
            #final_json.append(outbound_json)""
        print("===")

    print(json.dumps(sub_jsons, indent=4))

    return sub_configs

    ""# 4. create template json

    ""final_json = {
        "outbounds": [],
        "inbounds": [
            {
            "address": [
                "172.19.0.1/30",
                "fdfe:dcba:9876::1/126"
            ],
            "auto_route": True,
            "endpoint_independent_nat": True,
            "mtu": 9000,
            "platform": {
                "http_proxy": {
                "enabled": True,
                "server": "127.0.0.1",
                "server_port": 2080
                }
            },
            "stack": "system",
            "strict_route": True,
            "type": "tun"
            },
            {
            "listen": "127.0.0.1",
            "listen_port": 2080,
            "type": "mixed",
            "users": []
            }
        ]
    }""

    # 5. create final json

    final_json = []

    for sub_json in sub_jsons:
        print("===")
        outbound_type = sub_json["outbounds"][0].get("type", sub_json["outbounds"][0].get("protocol", None))
        print("outbound_type", outbound_type)
        print(sub_json)

        if outbound_type in ("naive", "vless"):
            final_json.append(sub_json)
            print("ADDED")
            #outbound_json = copy.deepcopy(template_json)
            #outbound_json["outbounds"] = [sub_json["outbounds"][0]]
            #print(outbound_json)
            #final_json.append(outbound_json)
        print("===")
    return final_json

    ""for sub_json in sub_jsons:
        for sub_outbound in sub_json["outbounds"]:
            print("=====")

            outbound_type = sub_outbound.get("type", sub_outbound.get("protocol", None))
            print("outbound_type", outbound_type)

            if outbound_type in ("naive", "vless"):

                #if sub_outbound.get("remarks")
                final_sub_outbound = copy.deepcopy(sub_outbound)
                #final_sub_outbound["protocol"] = outbound_type

                #if "type" in final_sub_outbound:
                #    del final_sub_outbound["type"]
                
                final_json["outbounds"].append(final_sub_outbound)
        
            print(sub_outbound)
            print("=====")

    return final_json""
    """



if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)