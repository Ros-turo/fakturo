from database import DBSession

class BaseRepo:

    def __init__(self, db: DBSession) -> None:
        self.db = db