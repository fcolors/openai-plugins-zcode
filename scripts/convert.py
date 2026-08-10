from pathlib import Path
import json
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = ROOT / "plugins"
REPOSITORY_RAW_URL = (
    "https://raw.githubusercontent.com/"
    "fcolors/openai-plugins-zcode/main"
)

# ZCode 当前支持的 plugin.json 字段
SUPPORTED_FIELDS = {
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
    "commands",
    "skills",
    "hooks",
    "mcpServers",
    "agents",
    "dependencies",
    "userConfig",
    # Preserve Codex UI metadata, including composerIcon and logo paths.
    "interface",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


marketplace_plugins = []

if not PLUGINS_DIR.exists():
    raise SystemExit("plugins directory not found")


for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
    if not plugin_dir.is_dir():
        continue

    codex_manifest = (
        plugin_dir
        / ".codex-plugin"
        / "plugin.json"
    )

    if not codex_manifest.exists():
        print(f"SKIP {plugin_dir.name}: no Codex manifest")
        continue

    try:
        source_manifest = read_json(codex_manifest)
    except Exception as exc:
        print(f"SKIP {plugin_dir.name}: {exc}")
        continue

    # 只保留 ZCode 支持的字段
    zcode_manifest = {
        key: value
        for key, value in source_manifest.items()
        if key in SUPPORTED_FIELDS
    }

    # name 是必需的
    zcode_manifest["name"] = source_manifest.get(
        "name",
        plugin_dir.name,
    )

    # 如果目录存在，但 Codex manifest 没有显式声明，
    # 帮它自动补上。
    if (
        (plugin_dir / "skills").is_dir()
        and "skills" not in zcode_manifest
    ):
        zcode_manifest["skills"] = "./skills/"

    if (
        (plugin_dir / "commands").is_dir()
        and "commands" not in zcode_manifest
    ):
        zcode_manifest["commands"] = "./commands/"

    if (
        (plugin_dir / "agents").is_dir()
        and "agents" not in zcode_manifest
    ):
        zcode_manifest["agents"] = "./agents/"

    if (
        (plugin_dir / ".mcp.json").exists()
        and "mcpServers" not in zcode_manifest
    ):
        zcode_manifest["mcpServers"] = "./.mcp.json"

    if (
        (plugin_dir / "hooks.json").exists()
        and "hooks" not in zcode_manifest
    ):
        zcode_manifest["hooks"] = "./hooks.json"

    if (
        (plugin_dir / "hooks" / "hooks.json").exists()
        and "hooks" not in zcode_manifest
    ):
        zcode_manifest["hooks"] = "./hooks/hooks.json"

    # 写 ZCode manifest
    zcode_dir = plugin_dir / ".zcode-plugin"
    zcode_dir.mkdir(parents=True, exist_ok=True)

    (zcode_dir / "plugin.json").write_text(
        json.dumps(
            zcode_manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    entry = {
        "name": zcode_manifest["name"],
        "source": f"./{plugin_dir.name}",
    }

    for key in ("description", "version"):
        if key in zcode_manifest:
            entry[key] = zcode_manifest[key]

    # ZCode reads marketplace card icons from plugins[].icon. It does not
    # use Codex's interface.logo/composerIcon fields for marketplace cards.
    interface = source_manifest.get("interface", {})
    icon_path = interface.get("logo") or interface.get("composerIcon")
    if isinstance(icon_path, str) and icon_path.startswith("./"):
        relative_icon_path = (
            Path("plugins")
            / plugin_dir.name
            / icon_path.removeprefix("./")
        ).as_posix()
        if (ROOT / relative_icon_path).is_file():
            entry["icon"] = (
                f"{REPOSITORY_RAW_URL}/"
                f"{quote(relative_icon_path, safe='/')}"
            )

    marketplace_plugins.append(entry)

    print(f"OK   {plugin_dir.name}")


marketplace = {
    "name": "openai-plugins-zcode",
    "description": (
        "OpenAI Codex plugins automatically adapted for ZCode"
    ),
    "pluginRoot": "plugins",
    "plugins": marketplace_plugins,
}

(ROOT / "marketplace.json").write_text(
    json.dumps(
        marketplace,
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)

print()
print(
    f"Generated {len(marketplace_plugins)} plugins"
)
