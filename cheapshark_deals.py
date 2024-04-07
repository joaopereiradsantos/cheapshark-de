from datetime import datetime, timedelta, timezone
import requests
import psycopg2
from psycopg2 import OperationalError
import json
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from secret_manager import get_secret

# Extract Deals that have been updated in the past hour
def extract_deals():
    try:
        all_deals = []
        base_url = 'https://www.cheapshark.com/api/1.0/deals'
        
        # Fetch the total number of pages
        response = requests.get(base_url, params={'maxAge': '1', 'pageNumber': 0})
        response.raise_for_status()  # Raise an exception for non-2xx status codes
        total_pages = int(response.headers.get('X-Total-Page-Count', 1))

        # Loop through each page and fetch data
        for page_number in range(total_pages):
            params = {'maxAge': '1', 'pageNumber': page_number}
            response = requests.get(base_url, params=params)
            if response.status_code == 429:
                raise TooManyRedirects("Too many requests to the API. Rate limit exceeded.")
            response.raise_for_status()  # Raise an exception for non-2xx status codes
            data = response.json()
            all_deals.extend(data)

        return all_deals
    except Exception as e:
        print("An error occurred while fetching data from the API:", e)
        raise  # Re-raise the exception to fail the task


def extract_games_cheapest_price_ever(**kwargs):
    ti = kwargs['ti']
    extracted_data = ti.xcom_pull(task_ids='extract_deals')
    # Count distinct dealID
    distinct_deal_ids = len(set(deal['dealID'] for deal in extracted_data))
    print("Number of distinct dealIDs:", distinct_deal_ids)
    # Process extracted data here
    game_ids = [deal['gameID'] for deal in extracted_data]
    game_details = {}
    
    # API allows up to 25 gameIDs per call, so we need to split the IDs into chunks
    chunk_size = 25
    for i in range(0, len(game_ids), chunk_size):
        chunk_ids = game_ids[i:i+chunk_size]
        ids_param = ','.join(str(id) for id in chunk_ids)
        url = f"https://www.cheapshark.com/api/1.0/games?ids={ids_param}"
        response = requests.get(url)
        data = response.json()
        game_details.update(data)
    
    print("Game details:", game_details)  # Add this line to inspect the structure
    
    # Extracting gameID and cheapestPriceEver price value
    game_prices = {game_id: details['cheapestPriceEver']['price'] for game_id, details in game_details.items()}
    print("Game prices:", game_prices)

    return game_prices


def aggregate_data(**kwargs):
    ti = kwargs['ti']
    extracted_data = ti.xcom_pull(task_ids='extract_deals')
    game_prices = ti.xcom_pull(task_ids='extract_games_cheapest_price_ever')

    # Join extracted_data with game_prices based on gameID
    aggregated_data = []
    for deal in extracted_data:
        game_id = deal['gameID']
        cheapest_price = game_prices.get(game_id)
        if cheapest_price is not None:
            # Convert releaseDate and lastChange from Unix timestamp to datetime UTC
            deal['releaseDate'] = datetime.fromtimestamp(deal['releaseDate'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            deal['lastChange'] = datetime.fromtimestamp(deal['lastChange'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            deal['cheapestPriceEver'] = cheapest_price
            aggregated_data.append(deal)

    print("Aggregated Data:", aggregated_data)
    return aggregated_data



def load_data_to_postgres(table_name, data, **kwargs):
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
        
        if table_name == 'games':
            for entry in data:
                cur.execute("""
                    INSERT INTO games (
                        game_id,
                        internal_name,
                        title,
                        metacritic_link,
                        metacritic_score,
                        steam_rating_text,
                        steam_rating_percent,
                        steam_rating_count,
                        steam_app_id,
                        release_date,
                        thumb,
                        cheapest_price_ever
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (game_id) DO NOTHING;
                """, (
                    entry['gameID'],
                    entry['internalName'],
                    entry['title'],
                    entry['metacriticLink'],
                    entry['metacriticScore'],
                    entry['steamRatingText'],
                    entry['steamRatingPercent'],
                    entry['steamRatingCount'],
                    entry['steamAppID'],
                    entry['releaseDate'],
                    entry['thumb'],
                    entry['cheapestPriceEver']
                ))
        elif table_name == 'deals':
            for entry in data:
                cur.execute("""
                    INSERT INTO deals (
                        deal_id,
                        store_id,
                        game_id,
                        sale_price,
                        normal_price,
                        is_on_sale,
                        savings,
                        deal_rating,
                        last_change
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (deal_id, last_change) DO UPDATE
                    SET store_id = excluded.store_id,
                        game_id = excluded.game_id,
                        sale_price = excluded.sale_price,
                        normal_price = excluded.normal_price,
                        is_on_sale = excluded.is_on_sale,
                        savings = excluded.savings,
                        deal_rating = excluded.deal_rating;
                """, (
                    entry['dealID'],
                    entry['storeID'],
                    entry['gameID'],
                    entry['salePrice'],
                    entry['normalPrice'],
                    entry['isOnSale'],
                    entry['savings'],
                    entry['dealRating'],
                    entry['lastChange']
                ))

        conn.commit()
    except OperationalError as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 4, 4),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'cheapshark_deals_dag',
    default_args=default_args,
    description='Extract data from CheapShark API',
    schedule_interval=None,
)

extract_task = PythonOperator(
    task_id='extract_deals',
    python_callable=extract_deals,
    dag=dag,
)

process_task = PythonOperator(
    task_id='extract_games_cheapest_price_ever',
    python_callable=extract_games_cheapest_price_ever,
    provide_context=True,
    dag=dag,
)

aggregate_task = PythonOperator(
    task_id='aggregate_data',
    python_callable=aggregate_data,
    provide_context=True,
    dag=dag,
)

load_games_task = PythonOperator(
    task_id='load_games_to_postgres',
    python_callable=load_data_to_postgres,
    op_args=['games', 'aggregated_data'],
    provide_context=True,
    dag=dag,
)

load_deals_task = PythonOperator(
    task_id='load_deals_to_postgres',
    python_callable=load_data_to_postgres,
    op_args=['deals', 'aggregated_data'],
    provide_context=True,
    dag=dag,
)

extract_task >> process_task >> aggregate_task >> [load_games_task, load_deals_task]