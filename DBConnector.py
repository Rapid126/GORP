import psycopg2
from psycopg2 import OperationalError,Error
from psycopg2.extras import execute_values

class DBConnector:
    # Database connection parameters as class constants
    HOST = "195.150.230.208"
    PORT = 5432
    USER = "z06"
    PASSWORD = "z06@2025"
    DATABASE = "z06"

    def __init__(self):
        self.connection = None

    def connect(self):

        if self.connection is None:
            try:
                self.connection = psycopg2.connect(
                    host=self.HOST,
                    port=self.PORT,
                    user=self.USER,
                    password=self.PASSWORD,
                    database=self.DATABASE
                )
                print("Database connection established.")
            except OperationalError as e:
                print(f"Failed to connect to database: {e}")
                raise
        else:
            print("Connection already open.")

    def disconnect(self):

        if self.connection:
            self.connection.close()
            self.connection = None
            print("Database connection closed.")
        else:
            print("No open connection to close.")

    def execute_query(self, query, params=None, fetch=False,use_execute_values=False):
        """
               Wykonuje zapytanie SQL podane w parametrach.

               Args:
                   query (str): Treść zapytania SQL do wykonania.
                   params (list lub tuple, opcjonalnie):
                       - pojedynczy krotka/lista wartości dla execute(),
                       - lub lista krotek/list dla ejecutemany().
                   fetch (bool):
                       - True, jeśli oczekujemy wyniku (SELECT),
                       - False, jeśli zapytanie modyfikuje dane (INSERT/UPDATE/DELETE).

               Returns:
                   list of tuples: Dane zwrócone przez zapytanie, jeśli fetch=True.
                   None: W innych przypadkach lub jeśli wystąpił błąd.

               Raises:
                   psycopg2.Error: W razie problemu z wykonaniem zapytania.
               """
        if self.connection is None:
            print("No database connection. Use connect() first.")
            return None

        try:
            with self.connection.cursor() as cursor:
                if use_execute_values:
                    execute_values(cursor, query, params)
                elif isinstance(params, list) and params and isinstance(params[0], (list, tuple)):
                    cursor.executemany(query, params)
                else:
                    cursor.execute(query, params)

                if fetch:
                    return cursor.fetchall()
                else:
                    self.connection.commit()
                    print("Query executed and committed.")
        except Error as e:
            print(f"Error executing query: {e}")
            self.rollback()
            return None

    def begin(self):
        """Rozpoczyna nową transakcję (jeśli autocommit jest włączony)."""
        if self.connection:
            self.connection.autocommit = False
            print("Transaction started.")
        else:
            print("No open connection to start transaction.")

    def commit(self):
        """Zatwierdza bieżącą transakcję."""
        if self.connection:
            try:
                self.connection.commit()
                print("Transaction committed.")
            except Error as e:
                print(f"Error committing transaction: {e}")
                self.rollback()
                raise

    def rollback(self):
        """Wycofuje bieżącą transakcję."""
        if self.connection:
            try:
                self.connection.rollback()
                print("Transaction rolled back.")
            except Error as e:
                print(f"Error during rollback: {e}")
                raise