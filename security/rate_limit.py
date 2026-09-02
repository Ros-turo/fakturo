from typing import Annotated

from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException

from dependencies import IPDepends
from logging_config import logger

class LoginAttempt:

    def __init__(self) -> None:

        self.attempt_count: int = 0
        self.timeout_to: datetime = datetime.now(timezone.utc)

    def check_timeout(self) -> bool:
        now = datetime.now(timezone.utc)

        return self.timeout_to < now

    def logging_attempt(self) -> None:

        self.attempt_count += 1

        if self.attempt_count > 2:
            self.timeout_to = datetime.now(timezone.utc) + timedelta(seconds=2 ** self.attempt_count)

        return None

    def clear_attempt(self) -> None:
        self.attempt_count = 0
        self.timeout_to = datetime.now(timezone.utc)

attempt_logger: dict[str, LoginAttempt] = {}

def get_la_inst(ip: IPDepends) -> LoginAttempt:

    if ip not in attempt_logger:
        new_ip = LoginAttempt()
        attempt_logger[ip] = new_ip

    return attempt_logger[ip]

LADepends = Annotated[LoginAttempt, Depends(get_la_inst)]

def check_timeout(inst: LADepends):
    logger.debug(f"Checking timeout for {inst}")
    if not inst.check_timeout():
        logger.debug(f"Blocked {inst}")
        raise HTTPException(status_code=423, detail="Account is blocked")