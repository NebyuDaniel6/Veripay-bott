# Simple in-memory state store for dev
from typing import Optional, Dict

class StateStore:
    def __init__(self):
        self.user_role: Dict[int, str] = {}
        self.selected_bank: Dict[int, Optional[str]] = {}
        self.step: Dict[int, Optional[str]] = {}
        self.last_ocr_text: Dict[int, Optional[str]] = {}

    def set_role(self, user_id: int, role: str) -> None:
        self.user_role[user_id] = role

    def get_role(self, user_id: int) -> str:
        return self.user_role.get(user_id, "waiter")

    def set_bank(self, user_id: int, bank: Optional[str]) -> None:
        self.selected_bank[user_id] = bank

    def get_bank(self, user_id: int) -> Optional[str]:
        return self.selected_bank.get(user_id)

    def set_step(self, user_id: int, step: Optional[str]) -> None:
        self.step[user_id] = step

    def get_step(self, user_id: int) -> Optional[str]:
        return self.step.get(user_id)

    def set_last_ocr_text(self, user_id: int, text: Optional[str]) -> None:
        self.last_ocr_text[user_id] = text

    def get_last_ocr_text(self, user_id: int) -> Optional[str]:
        return self.last_ocr_text.get(user_id)
