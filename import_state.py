import csv
import psycopg2
from psycopg2 import sql
import logging
from typing import List, Tuple
from config import read_env_file

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    level=logging.DEBUG 
)
logger = logging.getLogger(__name__)

class CSVPostgresUpdater:
    def __init__(self, db_config: dict):
        """
        Initialize the updater with database configuration.
        
        Args:
            db_config (dict): Database configuration with keys: host, database, user, password, port
        """
        self.db_config = db_config
        self.connection = None
    
    def connect_to_db(self):
        """Establish connection to PostgreSQL database."""
        try:
            self.connection = psycopg2.connect(
                host=self.db_config['host'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                port=self.db_config.get('port', 5432)
            )
            logger.info("Successfully connected to PostgreSQL database")
        except psycopg2.Error as e:
            logger.error(f"Error connecting to PostgreSQL database: {e}")
            raise
    
    def read_csv_data(self, csv_file_path: str) -> List[Tuple[str, str]]:
        """
        Read CSV file and return list of (incident_number, state) tuples.
        
        Args:
            csv_file_path (str): Path to the CSV file
            
        Returns:
            List[Tuple[str, str]]: List of (incident_number, state) pairs
        """
        incident_number_col = "issue_key"
        state_col = "state"
        data = []
        try:
            with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                # Check if required columns exist
                if incident_number_col not in reader.fieldnames or state_col not in reader.fieldnames:
                    logger.error(f"CSV file must contain '{incident_number_col}' and '{state_col}' columns")
                    raise ValueError(f"CSV file must contain '{incident_number_col}' and '{state_col}' columns")
                
                logger.info(f"Successfully read CSV file: {csv_file_path}")

                for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
                    logger.debug(f"Processing row {row_num}")
                    try:
                        incident_number = row[incident_number_col].strip()
                        state = row[state_col].strip()
                        logger.debug(f"incident_number: {incident_number}, state: {state}")
                        
                        if not incident_number:
                            logger.warning(f"Empty incident_number in row {row_num}, skipping")
                            continue
                        
                        if not state:
                            logger.warning(f"Empty state for {incident_number} in row {row_num}, skipping")
                            continue
                        
                        data.append((incident_number, state))
                    except Exception as e:
                        logger.error(f"Error processing row {row_num}: {e}")
                        logger.debug(f"Row data: {row}")
                        continue
                    continue
            
            logger.info(f"Successfully read {len(data)} records from CSV file: {csv_file_path}")
            return data
            
        except FileNotFoundError:
            logger.error(f"CSV file not found: {csv_file_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            raise
    
    def update_database(self, data: List[Tuple[str, str]], table_name: str = 'bugs'):
        """
        Update PostgreSQL database with CSV data.
        
        Args:
            data (List[Tuple[str, str]]): List of (incident_number, state) pairs
            table_name (str): Name of the table to update (default: 'bugs')
        """
        if not self.connection:
            raise Exception("No database connection. Call connect_to_db() first.")
        
        cursor = self.connection.cursor()
        updated_count = 0
        not_found_count = 0
        
        try:
            # Prepare the UPDATE statement
            update_query = sql.SQL("""
                UPDATE {table} 
                SET state = %s 
                WHERE incident_number = %s
            """).format(table=sql.Identifier(table_name))
            
            for incident_number, state in data:
                try:
                    cursor.execute(update_query, (state, incident_number))
                    
                    if cursor.rowcount > 0:
                        updated_count += 1
                        logger.debug(f"Updated issue_key {incident_number} to state {state}")
                    else:
                        not_found_count += 1
                        logger.warning(f"No record found with issue_key: {incident_number}")
                        
                except psycopg2.Error as e:
                    logger.error(f"Error updating record {incident_number}: {e}")
                    self.connection.rollback()
                    raise
            
            # Commit all changes
            self.connection.commit()
            logger.info(f"Database update completed: {updated_count} records updated, {not_found_count} not found")
            
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Database update failed: {e}")
            raise
        finally:
            cursor.close()
    
    def close_connection(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def process_csv_update(self, csv_file_path: str, table_name: str = 'bugs'):
        """
        Complete process: read CSV and update database.
        
        Args:
            csv_file_path (str): Path to the CSV file
            table_name (str): Name of the table to update (default: 'issues')
        """
        try:
            # Connect to database
            self.connect_to_db()
            
            # Read CSV data
            csv_data = self.read_csv_data(csv_file_path)
            
            if not csv_data:
                logger.warning("No valid data found in CSV file")
                return
            
            # Update database
            self.update_database(csv_data, table_name)
            
        except Exception as e:
            logger.error(f"Process failed: {e}")
            raise
        finally:
            self.close_connection()


def main():
    """Main function to run the CSV to PostgreSQL updater."""
    env_vars = read_env_file()
    
    # Database configuration - update these values for your setup
    db_config = {
        'host': env_vars.get('DB_HOST', 'localhost'),
        'database': env_vars.get('DB_NAME', 'your_database'),
        'user': env_vars.get('DB_USERNAME', 'your_username'),
        'password': env_vars.get('DB_PASSWORD', 'your_password'),
        'port': int(env_vars.get('DB_PORT', '5432'))
    }
    
    # CSV file path
    csv_file_path = 'data.csv'  # Update this path
    
    # Table name (update if different)
    table_name = 'bugs'
    
    # Create updater instance and process
    updater = CSVPostgresUpdater(db_config)
    
    try:
        updater.process_csv_update(csv_file_path, table_name)
        print("Update process completed successfully!")
        
    except Exception as e:
        print(f"Update process failed: {e}")


if __name__ == "__main__":
    main()