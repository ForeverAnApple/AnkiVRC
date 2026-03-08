from __future__ import annotations

from typing import Any, Iterable

from aqt import mw


def _debug_log(message: str, enabled: bool) -> None:
    if enabled:
        print(message)


class AnkiStatusProvider:
    def __init__(self, debug: bool = False) -> None:
        self.debug = debug

    def cards_left(self) -> int:
        if not getattr(mw, "col", None):
            _debug_log(
                "AnkiVRC: cards_left requested without loaded collection", self.debug
            )
            return 0

        try:
            due_total = 0
            for deck_info in self._iter_due_nodes(mw.col.sched.deckDueTree()):
                due_total += self._sum_due_counts(deck_info)
            _debug_log(f"AnkiVRC: calculated cards left = {due_total}", self.debug)
            return max(due_total, 0)
        except Exception as exc:
            print(f"AnkiVRC: failed to calculate cards left: {exc}")
            return 0

    def cards_done_today(self) -> int:
        if not getattr(mw, "col", None):
            _debug_log(
                "AnkiVRC: cards_done_today requested without loaded collection",
                self.debug,
            )
            return 0

        try:
            anki_today_start = int((mw.col.sched.day_cutoff - 86400) * 1000)
            reviews_today = mw.col.db.scalar(
                "SELECT COUNT(*) FROM revlog WHERE id > ?",
                anki_today_start,
            )
            _debug_log(
                f"AnkiVRC: calculated cards done today = {int(reviews_today or 0)}",
                self.debug,
            )
            return int(reviews_today or 0)
        except Exception as exc:
            print(f"AnkiVRC: failed to calculate cards done today: {exc}")
            return 0

    def _iter_due_nodes(self, deck_tree: Any) -> Iterable[Any]:
        if deck_tree is None:
            return ()
        if isinstance(deck_tree, (list, tuple)):
            return deck_tree
        return (deck_tree,)

    def _sum_due_counts(self, deck_info: Any) -> int:
        if isinstance(deck_info, (list, tuple)):
            if len(deck_info) >= 5:
                due = int(deck_info[2] or 0)
                learning = int(deck_info[3] or 0)
                new = int(deck_info[4] or 0)
                return due + learning + new
            return 0

        due = self._read_count(deck_info, "review_count", "reviewCount", "due")
        learning = self._read_count(deck_info, "learn_count", "learnCount", "lrn")
        new = self._read_count(deck_info, "new_count", "newCount", "new")
        return due + learning + new

    def _read_count(self, deck_info: Any, *names: str) -> int:
        for name in names:
            value = getattr(deck_info, name, None)
            if value is not None:
                return int(value or 0)
        return 0
