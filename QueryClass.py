class Query:
    @staticmethod
    def controllo(chat_id, user_id, user_full_name, data):
        return (
            f"MATCH (g:Group {{chat_id: {chat_id}}})-[:HAS_USER]->(u:User {{id: {user_id}}}) "
            "WITH u, CASE WHEN u.total + 1 > u.record THEN 1 ELSE 0 END as result "
            f"SET u.total = u.total + 1, u.fulltotal = u.fulltotal + 1, u.nome = '{user_full_name}', "
            f"u.ultimadata = '{data}', u.record = CASE WHEN u.total + 1 > u.record THEN u.total + 1 ELSE u.record END "
            "WITH u, result "
            "RETURN u.total as total, u.fulltotal as fulltotal, u.record as record, result"
        )

    @staticmethod
    def reset_all():
        return (
            "MATCH (u:User) "
            "SET u.total = 0"
        )

    @staticmethod
    def set_dataReset(data):
        return (
            "MATCH (d:DataReset) "
            f"SET d.data = '{data}' "
        )

    @staticmethod
    def get_dataReset():
        return (
            "MATCH (d:DataReset) "
            "RETURN d.data as data"
        )

    @staticmethod
    def registrazione(chat_id, user_id, user_full_name, data):
        return (
            f"MERGE (g:Group {{chat_id: {chat_id}}}) "
            f"CREATE (u:User {{nome: '{user_full_name}', id: {user_id}, total: 0, fulltotal: 0, record: 0, ultimadata: '{data}'}}) "
            "MERGE (g)-[:HAS_USER]->(u)"
        )

    @staticmethod
    def winner(chat_id):
        return (
            f"MATCH (g:Group {{chat_id: {chat_id}}})-[:HAS_USER]->(u:User) "
            "WHERE u.total <> 0 "
            "RETURN u.nome as nome, u.total as total, u.ultimadata as ultimadata "
            "ORDER BY u.total DESC, u.ultimadata"
        )

    @staticmethod
    def profilo(chat_id, user_id):
        return (
            f"MATCH (g:Group {{chat_id: {chat_id}}})-[:HAS_USER]->(u:User {{id: {user_id}}}) "
            "RETURN u.total, u.fulltotal, u.record"
        )

    @staticmethod
    def classifica(chat_id):
        return (
            f"MATCH (g:Group {{chat_id: {chat_id}}})-[:HAS_USER]->(u:User) "
            "WHERE u.total <> 0 "
            "RETURN u.nome as nome, u.total as total, u.ultimadata as ultimadata "
            "ORDER BY u.total DESC, u.ultimadata"
        )

    @staticmethod
    def classifica_totale(chat_id):
        return (
            f"MATCH (g:Group {{chat_id: {chat_id}}})-[:HAS_USER]->(u:User) "
            "WHERE u.fulltotal <> 0 "
            "RETURN u.nome as nome, u.fulltotal as fulltotal, u.ultimadata as ultimadata "
            "ORDER BY u.fulltotal DESC, u.ultimadata"
        )

    @staticmethod
    def record(chat_id):
        return (
            f"MATCH (g:Group {{chat_id: {chat_id}}})-[:HAS_USER]->(u:User) "
            "WHERE u.record <> 0 "
            "RETURN u.nome as nome, u.record as record, u.ultimadata as ultimadata "
            "ORDER BY u.record DESC, u.ultimadata"
        )

    @staticmethod
    def sorpasso(chat_id, total):
        return (
            f"MATCH (g:Group {{chat_id: {chat_id}}})-[:HAS_USER]->(u:User) "
            f"WHERE u.total = {total} AND u.total <> 0 "
            "RETURN u.nome as nome "
            "ORDER BY u.total DESC, u.ultimadata"
        )