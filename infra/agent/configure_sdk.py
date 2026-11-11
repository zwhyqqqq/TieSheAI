"""Create a local SDK credential through the existing simple Web login flow.

No secret is printed. Existing configuration is never overwritten. This helper
is specific to the local T01-A deployment with basic/password login disabled.
"""
import json
import os
from pathlib import Path
import subprocess
import uuid

import requests


def main():
    os.umask(0o077)
    infra = Path(__file__).resolve().parents[1]
    target = infra / ".local/agent/clearml.conf"
    if target.exists():
        if target.stat().st_mode & 0o077:
            raise RuntimeError("Existing SDK config permissions must be 0600")
        print("Preserved existing local SDK config:", target)
        return
    http = requests.Session()
    http.trust_env = False
    api = "http://127.0.0.1:8008/"

    def call(endpoint, body=None, **kwargs):
        response = http.post(api + endpoint, json=body or {}, timeout=20, **kwargs)
        response.raise_for_status()
        result = response.json()
        if result["meta"]["result_code"] != 200:
            raise RuntimeError("API rejected " + endpoint)
        return result["data"]

    modes = call("login.supported_modes")
    if modes["basic"]["enabled"]:
        raise RuntimeError("Password login is enabled; use an existing user's API keys")
    # The simple Web registration flow uses this configured bootstrap identity.
    # Read it in memory from the running release image, never from Fork defaults.
    code = (
        "import json; from apiserver.config_repo import config; "
        "print('BOOTSTRAP_JSON=' + json.dumps({'web': dict(config.get("
        "'secure.credentials.webserver')), 'company': config.get("
        "'apiserver.default_company')}))"
    )
    proc = subprocess.run(
        ["bash", str(infra / "compose.sh"), "exec", "-T", "apiserver", "python3", "-c", code],
        check=True, capture_output=True, text=True,
    )
    bootstrap = json.loads(next(
        line.partition("=")[2] for line in proc.stdout.splitlines()
        if line.startswith("BOOTSTRAP_JSON=")
    ))
    web = bootstrap["web"]
    auth = (web["user_key"], web["user_secret"])
    name = "TieSheAI T01-B CPU"
    users = call("users.get_all", auth=auth).get("users", [])
    matches = [user for user in users if user.get("name") == name]
    if len(matches) > 1:
        raise RuntimeError("Ambiguous existing smoke-test user")
    user_id = matches[0]["id"] if matches else call("auth.create_user", {
        "name": name, "company": bootstrap["company"],
        "email": str(uuid.uuid4()) + "@test.ai", "given_name": "TieSheAI",
        "family_name": "T01-B CPU",
    }, auth=auth)["id"]
    token = call("auth.login", auth=auth, headers={
        "X-ClearML-Impersonate-As": user_id,
    })["token"]
    credentials = call("auth.create_credentials", {"label": "TieSheAI T01-B CPU Agent"},
                       headers={"Authorization": "Bearer " + token})["credentials"]
    template = (infra / "agent/clearml.conf.example").read_text()
    for field, placeholder in [("access_key", "REPLACE_ACCESS_KEY"),
                               ("secret_key", "REPLACE_SECRET_KEY")]:
        template = template.replace(json.dumps(placeholder), json.dumps(credentials[field]))
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with target.open("x") as stream:
        stream.write(template)
    print("Created local SDK config (0600):", target)
    print("Registered SDK user:", user_id, name)


if __name__ == "__main__":
    main()
