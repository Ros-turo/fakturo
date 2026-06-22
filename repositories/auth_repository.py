from database import DBSession

class AuthRepo:

    def __init__(self,db:DBSession):
        self.db = db

