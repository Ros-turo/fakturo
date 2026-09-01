from schemas import Status


class AuthError(Exception):
    pass


class CredentialsError(AuthError):
    pass

class InvalidCredentialsError(CredentialsError):
    def __init__(self):
        super().__init__("Invalid credentials")

class EmailExistError(CredentialsError):

    def __init__(self):
        super().__init__("Email already exists")

class RateLimitError(AuthError):

    def __init__(self):
        super().__init__("You used too many attempts per time")

class UnauthorizedError(AuthError):

    def __init__(self):
        super().__init__("User is not authorized")

class UserInBlacklistError(AuthError):

    def __init__(self):
        super().__init__("User is blocked")

class UserInactiveError(AuthError):

    def __init__(self):
        super().__init__("User is inactive")

class TokenError(AuthError):
    pass

class InvalidTokenError(TokenError):

    def __init__(self, reason):
        self.reason = reason

class ExpiredTokenError(TokenError):

    def __init__(self):
        super().__init__("Token has expired")

class RevokedTokenError(TokenError):

    def __init__(self):
        super().__init__("Token is revoked")


class FakturoNotFoundError(Exception):

    def __init__(self, resource_name:str, resource_id:int | None = None):
        self.resource_name = resource_name
        self.resource_id = resource_id

class InvoiceNotFoundError(FakturoNotFoundError):

    def __init__(self, invoice_id: int):
        super().__init__(resource_name="Invoice", resource_id=invoice_id)

class UserNotFoundError(FakturoNotFoundError):

    def __init__(self, user_id: int):
        super().__init__(resource_name="User", resource_id=user_id)

class ClientNotFoundError(FakturoNotFoundError):

    def __init__(self, client_id):
        super().__init__(resource_name="Client", resource_id=client_id)

class RefreshTokenNotFoundError(FakturoNotFoundError):

    def __init__(self):
        super().__init__(resource_name="Refresh token")

class DeviceNotFoundError(FakturoNotFoundError):

    def __init__(self):
        super().__init__(resource_name="Device")



class FakturoDeleteError(Exception):

    def __init__(self, resource_name, exc_reason):
        self.resource_name = resource_name
        self.resource_reason = exc_reason

class InvoiceDeleteError(FakturoDeleteError):

    def __init__(self, resource_reason):
        super().__init__(resource_name="Invoice", exc_reason=resource_reason)



class FakturoConflictError(Exception):

    def __init__(self, resource_name, exc_detail):
        self.resource_name = resource_name
        self.exc_detail = exc_detail

class InvoiceConflict(FakturoConflictError):

    def __init__(self, exc_detail):
        super().__init__(resource_name="Invoice", exc_detail=exc_detail)



class BusinessRuleError(Exception):

    def __init__(self, rule_name: str, detail: str):

        self.rule = rule_name
        self.detail = detail

class InvalidStatusChangeError(BusinessRuleError):
    
    def __init__(self, from_status:Status, to_status:Status):
        super().__init__(rule_name="Invalid changing status",
                         detail= f"You cannot change status from {from_status.value} to {to_status.value}")

class CeleryError(Exception):
    pass

class InvoiceNotFound(CeleryError):

    def __init__(self, invoice_id: int, uid:int):
        self.invoice_id = invoice_id
        self.uid = uid
        super().__init__(f"Failed to find invoice: {invoice_id} for user: {uid}")