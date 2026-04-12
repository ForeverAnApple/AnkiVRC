# AnkiVRC
Anki cards status for VRChat

## Requirements
- [OSC](https://docs.vrchat.com/docs/osc-overview) Enabled in VRChat.

## Config
- `update_interval_seconds`: how often review status is sent while you are in Anki review mode.
- The default is `10` seconds.
- The minimum is `1` second to avoid overly aggressive chatbox sends; this follows the `1 second` cooldown used in `references/vrcosc-magicchatbox/vrcosc-magicchatbox/Classes/DataAndSecurity/OSCSender.cs:12`.

## Nix packaging

The add-on root is the **repository root** — all required files (`__init__.py`, `config.json`, `osc_sender.py`, `status_provider.py`) live at the top level. No submodules, no build steps, no generated artifacts.

- **`sourceRoot`**: not needed (add-on is at repo root)
- **`fetchSubmodules`**: not needed (no submodules)
- **Runtime dependencies**: none beyond Anki itself (the add-on uses only Anki's bundled Python and Qt)

```nix
pkgs.anki-utils.buildAnkiAddon (finalAttrs: {
  pname = "anki-vrc";
  version = "unstable-2026-04-11";

  src = pkgs.fetchFromGitHub {
    owner = "ForeverAnApple";
    repo = "AnkiVRC";
    rev = "f48bea43e0e8f2c0d4e1b..."; # or a tag
    hash = "sha256-...";
  };

  meta = {
    description = "Send Anki review status to VRChat via OSC";
    homepage = "https://github.com/ForeverAnApple/AnkiVRC";
    license = lib.licenses.asl20;
  };
})
```

> **Note:** `README.md`, `LICENSE`, and `.gitignore` are also at the root but are harmless — Anki ignores files it doesn't recognize. If `buildAnkiAddon` has a file filter, only `__init__.py`, `config.json`, `osc_sender.py`, and `status_provider.py` are needed.
