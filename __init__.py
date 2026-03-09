from __future__ import annotations

import atexit
from typing import Any

from anki.hooks import addHook
from aqt import mw
from aqt.qt import QTimer

from .osc_sender import VRCHAT_CHATBOX_LIMIT, VRChatOscSender
from .status_provider import AnkiStatusProvider


DEFAULT_CONFIG = {
    "osc_host": "127.0.0.1",
    "osc_port": 9000,
    "update_interval_seconds": 10,
    "message_template": "Anki: {left} left | {done} done today",
    "done_message_template": "Anki: Done for today! | {done} done today",
    "clear_status_on_exit": True,
    "debug": False,
}

MIN_UPDATE_INTERVAL_SECONDS = 1


def _debug_log(message: str, enabled: bool) -> None:
    if enabled:
        print(message)


class ReviewStatusController:
    def __init__(self) -> None:
        self.status_provider = AnkiStatusProvider()
        self.timer: QTimer | None = None
        self.sender: VRChatOscSender | None = None
        self.config = dict(DEFAULT_CONFIG)
        self._sent_initial_update = False

    def on_profile_loaded(self) -> None:
        self.config = self._load_config()
        self.status_provider = AnkiStatusProvider(debug=self._debug_enabled())
        self._close_sender()
        self.sender = VRChatOscSender(
            self.config["osc_host"],
            self.config["osc_port"],
            debug=self._debug_enabled(),
        )
        self._sent_initial_update = False
        _debug_log("AnkiVRC: profile loaded", self._debug_enabled())

        if self.timer is None:
            self.timer = QTimer(mw)
            self.timer.timeout.connect(self._send_review_status)
            _debug_log("AnkiVRC: review timer created", self._debug_enabled())

        self.timer.setInterval(self.config["update_interval_seconds"] * 1000)
        _debug_log(
            "AnkiVRC: config loaded "
            f"host={self.config['osc_host']} port={self.config['osc_port']} "
            f"interval={self.config['update_interval_seconds']} clear_on_exit={self.config['clear_status_on_exit']} "
            f"debug={self.config['debug']}",
            self._debug_enabled(),
        )

        if getattr(mw, "state", None) == "review":
            self._start_review_updates(reason="profile_loaded_in_review")

    def on_state_change(self, new_state: str, old_state: str) -> None:
        _debug_log(
            f"AnkiVRC: state change {old_state!r} -> {new_state!r}",
            self._debug_enabled(),
        )
        if new_state == "review":
            self._start_review_updates(reason="entered_review")
            return

        if old_state == "review":
            self._stop_review_updates(clear_status=self.config["clear_status_on_exit"])

    def on_profile_unloaded(self) -> None:
        _debug_log("AnkiVRC: profile unloading", self._debug_enabled())
        self._stop_review_updates(clear_status=self.config["clear_status_on_exit"])
        self._close_sender()

    def _start_review_updates(self, reason: str) -> None:
        _debug_log(
            f"AnkiVRC: starting review updates ({reason})", self._debug_enabled()
        )
        if self.timer is None or self.sender is None:
            self.on_profile_loaded()

        if self.timer is None:
            _debug_log(
                "AnkiVRC: review updates aborted because timer is unavailable",
                self._debug_enabled(),
            )
            return

        self.timer.start()
        _debug_log("AnkiVRC: review timer started", self._debug_enabled())

        if not self._sent_initial_update:
            self._send_review_status(reason=f"initial_{reason}")
            self._sent_initial_update = True
        else:
            self._send_review_status(reason=reason)

    def _stop_review_updates(self, clear_status: bool) -> None:
        _debug_log(
            f"AnkiVRC: stopping review updates | clear_status={clear_status}",
            self._debug_enabled(),
        )
        if self.timer is not None:
            self.timer.stop()
            _debug_log("AnkiVRC: review timer stopped", self._debug_enabled())

        self._sent_initial_update = False

        if clear_status:
            self._clear_chatbox()

    def _send_review_status(self, reason: str = "timer") -> None:
        current_state = getattr(mw, "state", None)
        _debug_log(
            f"AnkiVRC: send status requested | reason={reason} | state={current_state!r}",
            self._debug_enabled(),
        )

        if current_state != "review":
            _debug_log(
                "AnkiVRC: skipping OSC send because Anki is not in review",
                self._debug_enabled(),
            )
            return

        if self.sender is None:
            _debug_log(
                "AnkiVRC: skipping OSC send because sender is unavailable",
                self._debug_enabled(),
            )
            return

        left = self.status_provider.cards_left()
        done = self.status_provider.cards_done_today()
        message = self._format_status_message(left=left, done=done)
        _debug_log(
            "AnkiVRC: prepared review status "
            f"left={left} done={done} length={len(message)} message={message!r}",
            self._debug_enabled(),
        )

        try:
            self.sender.send_chatbox_message(message, send=True, effect=False)
        except OSError as exc:
            print(f"AnkiVRC: failed to send OSC message: {exc}")

    def _clear_chatbox(self) -> None:
        if self.sender is None:
            _debug_log(
                "AnkiVRC: clear requested but sender is unavailable",
                self._debug_enabled(),
            )
            return

        try:
            _debug_log("AnkiVRC: clearing VRChat chatbox", self._debug_enabled())
            self.sender.clear_chatbox()
        except OSError as exc:
            print(f"AnkiVRC: failed to clear VRChat chatbox: {exc}")

    def _close_sender(self) -> None:
        if self.sender is not None:
            _debug_log("AnkiVRC: disposing OSC sender", self._debug_enabled())
            self.sender.close()
            self.sender = None

    def _load_config(self) -> dict[str, Any]:
        config = dict(DEFAULT_CONFIG)
        loaded = mw.addonManager.getConfig(__name__) or {}
        config.update(loaded)

        raw_interval = loaded.get(
            "update_interval_seconds",
            loaded.get(
                "update_interval",
                DEFAULT_CONFIG["update_interval_seconds"],
            ),
        )

        config["osc_host"] = str(config["osc_host"] or DEFAULT_CONFIG["osc_host"])
        config["osc_port"] = self._safe_int(
            config["osc_port"], DEFAULT_CONFIG["osc_port"]
        )
        config["update_interval_seconds"] = max(
            MIN_UPDATE_INTERVAL_SECONDS,
            self._safe_int(raw_interval, DEFAULT_CONFIG["update_interval_seconds"]),
        )
        config["message_template"] = str(
            config["message_template"] or DEFAULT_CONFIG["message_template"]
        )
        config["done_message_template"] = str(
            config["done_message_template"] or DEFAULT_CONFIG["done_message_template"]
        )
        config["clear_status_on_exit"] = bool(config["clear_status_on_exit"])
        config["debug"] = bool(config.get("debug", DEFAULT_CONFIG["debug"]))

        if (
            self._safe_int(raw_interval, DEFAULT_CONFIG["update_interval_seconds"])
            < MIN_UPDATE_INTERVAL_SECONDS
        ):
            print(
                "AnkiVRC: update interval below VRChat-safe minimum; "
                f"using {MIN_UPDATE_INTERVAL_SECONDS} second(s) instead"
            )

        return config

    def _format_status_message(self, left: int, done: int) -> str:
        template_key = "done_message_template" if left <= 0 else "message_template"
        fallback_key = (
            "done_message_template"
            if template_key == "message_template"
            else "message_template"
        )

        values = {"left": max(left, 0), "done": max(done, 0)}
        message = self._render_template(self.config[template_key], values)

        if len(message) <= VRCHAT_CHATBOX_LIMIT:
            _debug_log("AnkiVRC: using configured template", self._debug_enabled())
            return message

        fallback_message = self._render_template(DEFAULT_CONFIG[template_key], values)
        if len(fallback_message) <= VRCHAT_CHATBOX_LIMIT:
            _debug_log(
                "AnkiVRC: configured template too long, using default fallback",
                self._debug_enabled(),
            )
            return fallback_message

        alternate_message = self._render_template(DEFAULT_CONFIG[fallback_key], values)
        if len(alternate_message) <= VRCHAT_CHATBOX_LIMIT:
            _debug_log(
                "AnkiVRC: primary fallback too long, using alternate fallback",
                self._debug_enabled(),
            )
            return alternate_message

        _debug_log(
            "AnkiVRC: all templates too long, truncating message",
            self._debug_enabled(),
        )
        return fallback_message[: VRCHAT_CHATBOX_LIMIT - 3] + "..."

    def _debug_enabled(self) -> bool:
        return bool(self.config.get("debug", False))

    def _render_template(self, template: str, values: dict[str, int]) -> str:
        try:
            return template.format(**values)
        except Exception:
            default_template = DEFAULT_CONFIG["message_template"]
            if values["left"] <= 0:
                default_template = DEFAULT_CONFIG["done_message_template"]
            return default_template.format(**values)

    def _safe_int(self, value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default


controller = ReviewStatusController()

addHook("profileLoaded", controller.on_profile_loaded)
addHook("afterStateChange", controller.on_state_change)
addHook("unloadProfile", controller.on_profile_unloaded)
atexit.register(controller.on_profile_unloaded)
