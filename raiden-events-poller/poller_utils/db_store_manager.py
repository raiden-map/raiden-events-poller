import mysql.connector
import sys

add_new_block_number_query = (
    "INSERT INTO produced_block(offset, block_number, event)" "VALUES (%s, %s, %s)"
)
update_block_number_query = "DELETE FROM produced_block WHERE event = %s"
add_token_network_query = (
    "INSERT INTO token_network (token_address, token_network_address, block_number)"
    "VALUES (%s, %s, %s)"
)
fetch_saved_token_network_query = "select * from token_network"
event_list_query = "select * from produced_block"
max_block_query = "select max( block_number ) as block_number from produced_block"
clean_produced_block_query = "delete from produced_block where block_number >= 0"

class dbStoreManager:
    def __init__(self):
        """Initialize connection to database
        
        Returns:    
            A database reference 
        """
        try:
            self.db = mysql.connector.connect(
                user="root",
                host="raiden-map-db-mysql.kafka.svc.cluster.local",
                password="",
                database="recovery_event",
            )
            self.cursor = self.db.cursor()
            self.cursor_dict = self.db.cursor(dictionary=True)
            # self.cursor.execute(clean_produced_block_query)
            # self.db.commit()

        except mysql.connector.Error as err:
            print(err)

        except Exception:
            sys.exit(1)

    def new_produced_block(
        self, offset, block_number, event, add_event_query=add_new_block_number_query
    ):
        """Add a produced event to the database"""

        data_event = (int(offset), int(block_number), str(event))

        try:
            self.cursor.execute(add_new_block_number_query, data_event)
            self.db.commit()
        except mysql.connector.Error as err:
            print(err)

    def update_block_number(
        self, event, block_number, update_block_number_query=update_block_number_query
    ):
        """Eliminates the record with the minimum block number based on the event"""

        data_event = str(event)
        try:
            self.cursor.execute(update_block_number_query, (data_event,))
            self.db.commit()
        except mysql.connector.Error as err:
            print(err)

    def event_list(self):
        """Returns:
                A list of last produced block based on event
        """
        try:
            self.cursor_dict.execute(event_list_query)
            self.db.commit()
        except mysql.connector.Error as err:
            print(err)
        return self.cursor_dict

    def max_block(self):
        """Returns:
                The last number of fully produced block
        """
        try:
            self.cursor_dict.execute(max_block_query)
            for row in self.cursor_dict:
                max_block_number = row["block_number"]
        except mysql.connector.Error as err:
            print(err)
        return max_block_number

    def save_token_network(
        self, token_address: str, token_network_address: str, block_number: int
    ):
        """Save new token newtworks created
        """
        try:
            data = (str(token_address), str(token_network_address), int(block_number))
            self.cursor.execute(add_token_network_query, data)
            self.db.commit()
        except mysql.connector.Error as err:
            print(err)

    def fetch_saved_token_network(self):
        """Returns:
            A list of all saved token networks
        """
        try:
            self.cursor_dict.execute(fetch_saved_token_network_query)
            self.db.commit()
        except mysql.connector.Error as err:
            print(err)
        return self.cursor_dict

