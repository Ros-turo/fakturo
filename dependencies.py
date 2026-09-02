from typing import Annotated

from fastapi import Request, Depends


def get_ip_address(request: Request) -> str:
    user = request.client
    if not user:
        return "Unknown"
    return user.host

IPDepends = Annotated[str, Depends(get_ip_address)]