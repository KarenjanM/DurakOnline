class Database:
    def __init__(self, connection, table):
        self.conn = connection
        self.table = table

    def exists_in_table(self, chat_id):
        q = self.table.select().where(self.table.c.chat_id == chat_id)
        result = self.conn.execute(q)
        if result.first() is None:
            return False
        else:
            return True


class UsersDatabase(Database):
    def select_by_id(self, chat_id):
        q = self.table.select().where(self.table.c.chat_id == chat_id)
        result = self.conn.execute(q)
        return result

    def select_by_username(self, username):
        q = self.table.select().where(self.table.c.username == username)
        result = self.conn.execute(q)
        return result

    def select_all(self):
        q = self.table.select()
        result = self.conn.execute(q)
        return result

    def insert(self, username, chat_id):
        q = self.table.insert().values(username=username, chat_id=chat_id)
        self.conn.execute(q)
        print(f'User {username} was added to the database')


class PartnersDatabase(Database):
    def select_by_id(self, chat_id):
        q = self.table.select().where(self.table.c.chat_id == chat_id)
        result = self.conn.execute(q)
        return result

    def insert(self, chat_id, partner_chat_id):
        q = self.table.insert().values(chat_id=chat_id, partner_chat_id=partner_chat_id)
        self.conn.execute(q)
        print(f'New pair is added to database')

    def delete_by_id(self, chat_id):
        q = self.table.delete().where(self.table.c.chat_id == chat_id)
        result = self.conn.execute(q)
        return result
