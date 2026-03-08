from __future__ import annotations

import socket
from typing import Any


CHATBOX_INPUT_ADDRESS = "/chatbox/input"
VRCHAT_CHATBOX_LIMIT = 144


def _debug_log(message: str, enabled: bool) -> None:
    if enabled:
        print(message)


class VRChatOscSender:
    def __init__(self, host: str, port: int, debug: bool = False) -> None:
        self.host = host
        self.port = int(port)
        self.debug = debug
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        _debug_log(f"AnkiVRC: OSC sender ready for {self.host}:{self.port}", self.debug)

    def send_chatbox_message(
        self, text: str, send: bool = True, effect: bool = False
    ) -> None:
        _debug_log(
            "AnkiVRC: sending OSC chatbox message "
            f"to {self.host}:{self.port} | send={send} effect={effect} | text={text!r}",
            self.debug,
        )
        message = self._encode_message(CHATBOX_INPUT_ADDRESS, text, send, effect)
        self._socket.sendto(message, (self.host, self.port))

    def clear_chatbox(self) -> None:
        self.send_chatbox_message("")

    def close(self) -> None:
        try:
            _debug_log(
                f"AnkiVRC: closing OSC sender for {self.host}:{self.port}", self.debug
            )
            self._socket.close()
        except OSError:
            pass

    def _encode_message(self, address: str, *arguments: Any) -> bytes:
        encoded = [self._pad_osc_string(address)]
        type_tags = [","]
        payload = []

        for argument in arguments:
            if isinstance(argument, str):
                type_tags.append("s")
                payload.append(self._pad_osc_string(argument))
            elif isinstance(argument, bool):
                type_tags.append("T" if argument else "F")
            elif isinstance(argument, int):
                type_tags.append("i")
                payload.append(int(argument).to_bytes(4, byteorder="big", signed=True))
            else:
                raise TypeError(f"Unsupported OSC argument type: {type(argument)!r}")

        encoded.append(self._pad_osc_string("".join(type_tags)))
        encoded.extend(payload)
        return b"".join(encoded)

    def _pad_osc_string(self, value: str) -> bytes:
        encoded = value.encode("utf-8") + b"\x00"
        padding = (-len(encoded)) % 4
        return encoded + (b"\x00" * padding)
