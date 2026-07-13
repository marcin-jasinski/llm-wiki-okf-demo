"""One-shot, idempotent setup for the demo xWiki instance (ticket 03).

Run after `docker compose up -d` (or `podman compose up -d`) in this directory:

    uv run docker/setup_xwiki.py [--skip-flavor]

Set XWIKI_ENGINE=podman to use Podman instead of Docker. The default
container name assumes each engine's compose naming convention; override
with XWIKI_CONTAINER if yours differs.

Targets localhost by default. To set up a remote instance, set XWIKI_BASE_URL
(e.g. http://your-host:8080) and, if this machine can't docker-exec into that
host directly, XWIKI_SSH_HOST (e.g. user@your-host or an ssh config alias) so
container commands run over ssh instead. Keep these in your shell env, not in
this file — it's committed to a public repo.

What it does:
1. Waits for xWiki REST to answer.
2. Enables the `superadmin` account (password below) and enables the
   markdown/1.2 syntax id, by appending to xwiki.cfg inside the container
   (persisted to the permanent-directory volume) and restarting it.
3. Installs the CommonMark Markdown Syntax 1.2 extension, and (unless
   --skip-flavor) the standard main-wiki flavor so the web UI works without
   the Distribution Wizard. Extensions can't be installed through the
   generic /rest/jobs endpoint (its XStream payload can't populate
   ExtensionId's final fields), so this uses the classic automation route:
   a superadmin-only Groovy page calling services.extension, executed via
   one authenticated GET, then deleted.
4. Verifies /rest/syntaxes lists markdown/1.2 and round-trips a markdown
   test page (create → read → delete).
"""

import os
import shlex
import subprocess
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("XWIKI_BASE_URL", "http://localhost:8080")
USER = "superadmin"
PASSWORD = "xwiki-demo"  # local demo instance only — not reachable from outside
ENGINE = os.environ.get("XWIKI_ENGINE", "docker")  # or "podman"
# docker compose v2 names containers "dir-service-1"; podman-compose uses "dir_service_1"
CONTAINER = os.environ.get(
    "XWIKI_CONTAINER", "docker-xwiki-1" if ENGINE == "docker" else "docker_xwiki_1"
)
# set to run ENGINE commands on a remote host instead of locally, e.g. "user@host" or an
# ssh config alias — needed when BASE_URL points at a container this machine can't docker-exec into
SSH_HOST = os.environ.get("XWIKI_SSH_HOST")
XWIKI_VERSION = "18.5.0"
MARKDOWN_EXTENSION = ("org.xwiki.contrib.markdown:syntax-markdown-commonmark12", "8.9")
FLAVOR = (
    "org.xwiki.platform:xwiki-platform-distribution-flavor-mainwiki",
    XWIKI_VERSION,
)

AUTH = (USER, PASSWORD)

INSTALL_SNIPPET = """{{{{groovy}}}}
def ext = services.extension
if (ext.installed.getInstalledExtension("{id}", "wiki:xwiki") != null) {{
  println("STATE: ALREADY_INSTALLED")
}} else {{
  def job = ext.install("{id}", "{version}", "wiki:xwiki")
  if (job == null) {{
    println("NOJOB: " + ext.lastError)
  }} else {{
    job.join()
    println("STATE: " + job.status.state)
    println("ERROR: " + job.status.error)
  }}
}}
{{{{/groovy}}}}"""

PAGE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<page xmlns="http://www.xwiki.org">
  <title>{title}</title>
  <syntax>{syntax}</syntax>
  <content>{content}</content>
</page>"""


def wait_for_rest(timeout=600):
    print(f"waiting for xWiki REST at {BASE_URL}…")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if httpx.get(f"{BASE_URL}/rest", timeout=5).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(5)
    sys.exit("xWiki REST did not come up — check `docker compose logs xwiki`")


def superadmin_works() -> bool:
    # a plain GET can 200 as guest regardless of credentials on an open wiki, so this
    # only trusts a write: create a scratch page and check who XWiki thinks authored it
    try:
        put_page("Setup", "AuthProbe", "auth probe", "probe")
    except httpx.HTTPStatusError:
        return False
    author = httpx.get(
        f"{BASE_URL}/rest/wikis/xwiki/spaces/Setup/pages/AuthProbe?media=json",
        auth=AUTH,
        timeout=30,
    ).json()["author"]
    delete_page("Setup", "AuthProbe")
    return author == f"XWiki.{USER}"


def engine_cmd(*args: str) -> list[str]:
    cmd = [ENGINE, *args]
    # ssh joins trailing args into one string for the remote shell to reparse, so without
    # quoting, "$CFG"/">>" etc. meant for the *inner* container sh -c get interpreted by
    # the *outer* remote shell instead — shlex.join keeps them a single opaque argument
    return ["ssh", SSH_HOST, shlex.join(cmd)] if SSH_HOST else cmd


def configure_container():
    if SSH_HOST:
        print(
            f"using ssh {SSH_HOST} for docker/podman commands — if it's not set up for "
            "passwordless (key-based) auth, you'll get a password prompt per command, "
            "and the restart step runs with output captured, which can hide that prompt "
            "and make the script look stuck. Set up an SSH key to the VPS to avoid this."
        )
    print("enabling superadmin + markdown syntax in xwiki.cfg, restarting container…")
    script = (
        'grep -q "^xwiki.superadminpassword=" $CFG || '
        f'echo "xwiki.superadminpassword={PASSWORD}" >> $CFG; '
        'grep -q "^xwiki.rendering.syntaxes=" $CFG || '
        'echo "xwiki.rendering.syntaxes=xwiki/2.1,markdown/1.2" >> $CFG; '
        "cp $CFG /usr/local/xwiki/xwiki.cfg; "
        # the flavor is installed by this script, so the Distribution Wizard
        # would only get in the way on first browse — turn it off
        'grep -q "^distribution.automaticStartOnMainWiki" $PROPS || '
        'echo "distribution.automaticStartOnMainWiki=false" >> $PROPS; '
        "cp $PROPS /usr/local/xwiki/xwiki.properties"
    )
    subprocess.run(
        engine_cmd(
            "exec",
            "-e",
            "CFG=/usr/local/tomcat/webapps/ROOT/WEB-INF/xwiki.cfg",
            "-e",
            "PROPS=/usr/local/tomcat/webapps/ROOT/WEB-INF/xwiki.properties",
            CONTAINER,
            "sh",
            "-c",
            script,
        ),
        check=True,
    )
    subprocess.run(engine_cmd("restart", CONTAINER), check=True, capture_output=True)
    wait_for_rest()


def put_page(space: str, name: str, title: str, content: str, syntax="xwiki/2.1"):
    xml = PAGE_XML.format(
        title=title,
        syntax=syntax,
        content=content.replace("&", "&amp;").replace("<", "&lt;"),
    )
    r = httpx.put(
        f"{BASE_URL}/rest/wikis/xwiki/spaces/{space}/pages/{name}",
        auth=AUTH,
        content=xml,
        headers={"Content-Type": "application/xml"},
        timeout=60,
    )
    r.raise_for_status()


def delete_page(space: str, name: str):
    httpx.delete(
        f"{BASE_URL}/rest/wikis/xwiki/spaces/{space}/pages/{name}",
        auth=AUTH,
        timeout=60,
    )


def install_extension(ext_id: str, version: str):
    print(f"installing {ext_id} {version} (may download for a while)…")
    put_page(
        "Setup",
        "Installer",
        "Extension installer",
        INSTALL_SNIPPET.format(id=ext_id, version=version),
    )
    # rendering the page runs the Groovy — generous timeout for the flavor
    r = httpx.get(
        f"{BASE_URL}/bin/get/Setup/Installer?outputSyntax=plain",
        auth=AUTH,
        timeout=3600,
    )
    delete_page("Setup", "Installer")
    out = r.text.strip()
    print(f"  -> {out}")
    ok = "STATE: FINISHED" in out and "ERROR: null" in out
    already = "STATE: ALREADY_INSTALLED" in out
    if not (ok or already):
        sys.exit(f"extension install failed:\n{out}")


def verify():
    syntaxes = httpx.get(
        f"{BASE_URL}/rest/syntaxes?media=json", auth=AUTH, timeout=30
    ).json()["syntaxes"]
    assert "markdown/1.2" in syntaxes, f"markdown/1.2 missing from {syntaxes}"
    put_page(
        "Demo",
        "SmokeTest",
        "REST smoke test",
        "# Hello\n\nThis is **markdown** stored in xWiki.\n",
        syntax="markdown/1.2",
    )
    page = httpx.get(
        f"{BASE_URL}/rest/wikis/xwiki/spaces/Demo/pages/SmokeTest?media=json",
        auth=AUTH,
        timeout=30,
    ).json()
    assert page["syntax"] == "markdown/1.2" and "**markdown**" in page["content"]
    delete_page("Demo", "SmokeTest")
    print("verified: markdown/1.2 listed, markdown page CRUD round-trips")


def main():
    wait_for_rest()
    if not superadmin_works():
        configure_container()
        if not superadmin_works():
            sys.exit("superadmin still not usable after configuration")
    install_extension(*MARKDOWN_EXTENSION)
    if "--skip-flavor" not in sys.argv:
        install_extension(*FLAVOR)
    verify()
    print(f"\nxWiki {XWIKI_VERSION} ready at {BASE_URL} — {USER} / {PASSWORD}")


if __name__ == "__main__":
    main()
