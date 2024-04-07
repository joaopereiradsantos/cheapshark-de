from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
import requests
import psycopg2
from psycopg2 import OperationalError
from secret_manager import get_secret

def extract_data():
    url = "https://www.cheapshark.com/api/1.0/stores"
    response = requests.get(url)
    stores_data = response.json()
    return stores_data

def load_data_to_postgres(**kwargs):
    stores_data = kwargs['ti'].xcom_pull(task_ids='extract_data_from_api')
    secret = get_secret("secret_name", "aws_region")  # to be modified
    conn_details = json.loads(secret)
    
    try:
        conn = psycopg2.connect(
            dbname=conn_details['dbname'],
            user=conn_details['username'],
            password=conn_details['password'],
            host=conn_details['host'],
            port=conn_details['port']
        )
        cur = conn.cursor()
        for store in stores_data:
            store_id = store['storeID']
            store_name = store['storeName']
            is_active = store['isActive']
            cur.execute("""
                INSERT INTO stores (store_id, store_name, is_active) 
                VALUES (%s, %s, %s) 
                ON CONFLICT (store_id) 
                DO UPDATE SET store_name = EXCLUDED.store_name;
            """, (store_id, store_name, is_active))
        conn.commit()
    except OperationalError as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 4, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'cheapshark_stores_dag',
    default_args=default_args,
    description='Extract stores data from Stores CheapShark API and load into stores table in PostgreSQL',
    schedule_interval=None, # Ad-hoc / Static table
    catchup=False, # Prevents backfilling
)

extract_task = PythonOperator(
    task_id='extract_data_from_stores',
    python_callable=extract_data,
    dag=dag,
)

load_task = PythonOperator(
    task_id='load_data_to_stores_postgres',
    python_callable=load_data_to_postgres,
    provide_context=True,  # This is set to True to provide context to the callable function
    dag=dag,
)

extract_task >> load_task
