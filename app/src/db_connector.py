import boto3
import json
import psycopg2
import pandas as pd

from app.src.logging import logger


class DatabaseConnector:

    def __init__(self,
                 database: str,
                 host: str,
                 port: int,
                 user: str,
                 password: str):
        self._connection = None
        self._connection_info = dict()
        self._connection_info["database"] = database
        self._connection_info["host"] = host
        self._connection_info["port"] = port
        self._connection_info["user"] = user
        self._connection_info["password"] = password
        self._get_connection()

    def _get_connection(self):
        dw_connection = psycopg2.connect(
            dbname=self._connection_info["database"],
            host=self._connection_info["host"],
            port=self._connection_info["port"],
            user=self._connection_info["user"],
            password=self._connection_info["password"])
        dw_connection.set_session(autocommit=True)
        self._connection = dw_connection
        return dw_connection

    def run_query(self, sql: str) -> pd.DataFrame:
        """
        Executes a query within the
        own established connection

        arg sql the sql string statement
             to execute
        """
        if self._connection is None:
            self._get_connection()
        try:
            cur = self._connection.cursor()
            cur.execute(sql)
            column_names = [desc[0] for desc in cur.description]
            result = cur.fetchall()
            cur.close()
            return pd.DataFrame(result, columns=column_names)
        except Exception as e:
            logger.error(str(e))
            logger.error(f"Error running query: {sql}")
            self._connection.rollback()
            raise
        finally:
            if self._connection is not None:
                self._connection.close()
                self._connection = None


def get_secret(client, secret):
    return client.get_secret_value(
        SecretId=secret
    )


def _get_connection_details(region_name: str, secret: str) -> dict:
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    get_secret_value_response = get_secret(client, secret)
    connection_info = json.loads(get_secret_value_response['SecretString'])
    # Checks if key db is present and map it to database
    if 'db' in connection_info:
        connection_info['database'] = connection_info['db']
    # Checks if user db is present and map it to username
    if 'user' in connection_info:
        connection_info['username'] = connection_info['user']
    # Checks if user pass is present and map it to password
    if 'pass' in connection_info:
        connection_info['password'] = connection_info['pass']
    return connection_info


def get_database_connector(connection_info: dict) -> DatabaseConnector:
    try:
        return DatabaseConnector(
            connection_info["database"],
            connection_info["host"],
            connection_info["port"],
            connection_info["username"],
            connection_info["password"]
        )
    except Exception as e:
        logger.error(f"Error while creating the connection to the database"
                     f"{e}")
        raise


def get_database_connector_arn(region: str, arn_secret: str) -> DatabaseConnector:
    return get_database_connector(_get_connection_details(region, arn_secret))