from datetime import datetime, timezone

from database import DBSession
from db_models import RefreshToken

from sqlalchemy import select

class AuthRepo:

    def __init__(self,db:DBSession):
        self.db = db

    async def get_refresh_token(self, jti: str) -> RefreshToken | None:

        token_data = await self.db.execute(select(RefreshToken)
                                           .where(RefreshToken.jti == jti))

        return token_data.scalar_one_or_none()

    async def post_refresh_token(self, uid: int, jti: str,
                                 expired_at: datetime, email: str):

        token_data = RefreshToken(
            jti = jti,
            expired_at = expired_at,
            user_id = uid,
            user_email = email
        )
        self.db.add(token_data)
        await self.db.commit()

        return None

    async def revoke_token(self, token:RefreshToken) -> None:

        token.revoked = True
        await self.db.commit()

    async def bulk_revoke_tokens(self, tokens: list[RefreshToken]):

        for token in tokens:
            token.revoked = True
        await self.db.commit()


    async def delete_token(self, token):
        await self.db.delete(token)
        await self.db.commit()

    async def get_actual_tokens(self, uid: int) -> list[RefreshToken]:
        now = datetime.now(timezone.utc)
        stmt = select(RefreshToken).where(RefreshToken.user_id == uid,
                                          RefreshToken.revoked == False,
                                          RefreshToken.expired_at > now)

        db_query = await self.db.execute(stmt)

        tokens = list(db_query.scalars().all())
        return tokens