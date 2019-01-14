import mysql.connector

add_event_query = "INSERT INTO saved_event" "(tx_hash, block_number)" "VALUES (%s, %s)"
update_block_number_query = (
    "DELETE FROM saved_event"
    "WHERE block_number <"
    "( SELECT maxo"
    "FROM ( SELECT MAX(block_number) AS maxo FROM saved_event) AS tmp)"
)
search_last_block_query = "SELECT max(block_number) " " FROM saved_event"


class dbStoreManager:
    def __init__(self):
        """Initialize connection to database
        
        Returns:
            A database reference 
        """
        self.db = mysql.connector.connect(
            user="root",
            host="raiden-map-db-mysql.kafka.svc.cluster.local",
            password="",
            database="ripristino",
        )
        self.cursor = self.db.cursor()

    def add_event(self, tx_hash, block_number):
        """Add a produced event to the database"""

        data_event = (str(tx_hash), int(block_number))

        self.cursor.execute(add_event_query, data_event)
        self.db.commit()

    def update_block_number(self):
        """Clean the database by deleting the numbers of fully produced blocks"""

        self.cursor.execute(update_block_number_query)
        self.db.commit()

    def search_last_block_number(self):
        """Search the biggest block number by which restore the Poller
        
        Returns: biggest block number"""

        self.cursor.execute(search_last_block_query)
        block_number = self.cursor.fetchall()

        return block_number[0][0]

