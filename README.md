# AnkiVRC
Anki cards status for VRChat

## Requirements
- [OSC](https://docs.vrchat.com/docs/osc-overview) Enabled in VRChat.

## Config
- `update_interval_seconds`: how often review status is sent while you are in Anki review mode.
- The default is `10` seconds.
- The minimum is `1` second to avoid overly aggressive chatbox sends; this follows the `1 second` cooldown used in `references/vrcosc-magicchatbox/vrcosc-magicchatbox/Classes/DataAndSecurity/OSCSender.cs:12`.
