<h1 align="center">Data Engineer Take Home Assignment</h1>

# Challenge
Thank you for your interest in joining our data engineering team.

In this take-home exercise you’ll be working in an imaginary company. The company’s product is a deal alert app for PC games. For this we will rely on the data provided by the [CheapShark API](https://apidocs.cheapshark.com/#c6e4678d-7ff0-ebd4-59c1-b4d0fb3dac87).

We are interested in keeping information about all the current deals per store. We want to be able to track when a deal has changed or is not available anymore. In order to create the alert we will also need detailed information of the game and the store related to that deal. 

Keep in mind the limitations offered by the API when you develop your solution.

As we know your time is valuable, please don't spend more than 4 hours on this assignment.

## Task 1
Create an Airflow DAG(s) that will fetch data from the CheapShark API every hour. The data that we are interested in is `Deals`, `Games` and `Stores` information.

## Task 2
Store the data obtained from task 1 in a RDBMS of your choice. Please include the DDL statements of the tables and a visual diagram of the model.

## Task 3
Create a query that shows how much has the price of a game increased in comparison to its `cheaper price ever` and its `costlier price ever`. The query must show the price increase in %, the name of the game, dealId of the costlier price ever and the name of the store of that deal.

## Task 4
Create a query that shows when a `Deal` is not available anymore or when a `Deal` is not on sale anymore.

## Task 5
Imagine that we become partners with CheapShark, and we agreed to get new and updated information from `Deals` through webhook events. Please describe how would you ingest this information to the database using any service(s) from the AWS ecosystem.

The expected input would have the following structure
```
[
  {
      "event": "deal.changed",
      "internalName": "DEUSEXHUMANREVOLUTIONDIRECTORSCUT",
      "title": "Deus Ex: Human Revolution - Director's Cut",
      "metacriticLink": "/game/pc/deus-ex-human-revolution---directors-cut",
      "dealID": "HhzMJAgQYGZ%2B%2BFPpBG%2BRFcuUQZJO3KXvlnyYYGwGUfU%3D",
      "storeID": "1",
      "gameID": "102249",
      "salePrice": "2.99",
      "normalPrice": "19.99",
      "isOnSale": "0",
      "savings": "85.042521",
      "metacriticScore": "91",
      "steamRatingText": "Very Positive",
      "steamRatingPercent": "92",
      "steamRatingCount": "17993",
      "steamAppID": "238010",
      "releaseDate": 1382400000,
      "lastChange": 1621536418,
      "dealRating": "9.6",
      "thumb": "https://cdn.cloudflare.steamstatic.com/steam/apps/238010/capsule_sm_120.jpg?t=1619788192"
   },
  {
    "event": "deal.new",
    "internalName": "THIEFDEADLYSHADOWS",
    "title": "Thief: Deadly Shadows",
    "metacriticLink": "/game/pc/thief-deadly-shadows",
    "dealID": "EX0oH20b7A1H2YiVjvVx5A0HH%2F4etw3x%2F6YMGVPpKbA%3D",
    "storeID": "1",
    "gameID": "396",
    "salePrice": "0.98",
    "normalPrice": "8.99",
    "isOnSale": "1",
    "savings": "89.098999",
    "metacriticScore": "85",
    "steamRatingText": "Very Positive",
    "steamRatingPercent": "81",
    "steamRatingCount": "1670",
    "steamAppID": "6980",
    "releaseDate": 1085443200,
    "lastChange": 1621540561,
    "dealRating": "9.4",
    "thumb": "https://cdn.cloudflare.steamstatic.com/steam/apps/6980/capsule_sm_120.jpg?t=1592493801"
  }
]
```

## Task 6
Please provide a documentation by updating this README.md about what you think important regarding your works in Task 1, 2 and 5.

# Submission
Please create a `private` github repo that contains this file along with your code and share with these users
- `dmartinez-ch` `chyzouakia`

So that we can see your commits or any activities you like to demonstrate!
Good luck!

____

## Initial Considerations

I began examining this challenge on April 4th, conducting an initial review of the API documentation and making some preliminary assumptions.

According to the API limitations, we're restricted to 150 calls per hour. Given this limit, we can extrapolate that we can fetch up to 216,000 games per day, considering there are currently 20 active stores, with an average of 10 deals per game.

For this challenge, let's prioritize the incremental mechanism over backfilling.

Before diving into the tasks, I had some lingering questions. To address them, I reached out to the API's creator and developer via Discord, posing inquiries about deal validity and the relationship between dealID and lastChange.

The response clarified that dealID represents a "deal" object in the database, which may or may not be on sale and can change price. The lastChange field indicates the last time the product's price was altered. The disappearance of a dealID would occur only if a product was removed or changed its name at a store.

Regarding Task 3, concerning the cheapest and costliest prices, I formulated a plan to retrieve the cheapestPriceEver via the API. However, I encountered ambiguity with the concept of the costliest price ever. Given the API's limitations, it seemed necessary to create a table to track price changes within the same dealID, possibly utilizing a composite primary key with dealID and lastChange.

Task 4 presented challenges in determining when a deal is no longer available. Based on the API creator's response, the only scenario in which a dealID disappears is if a product is removed or its name changed at a store. Thus, the only way to check if a deal is still available is by calling the deals endpoint with the respective dealID and confirming if a response is received. However, caching this information isn't scalable due to the linear increase in dealIDs.

These considerations will guide our approach to tackling the tasks effectively.

## Task 1 & 2
### Stores

In the Stores section of the API documentation, we discover that including the lastChange parameter in the Stores endpoint response provides us with a mapping of storeIDs to their last update/change time. This feature is particularly useful for reducing the number of API requests for deals or games.

Upon initial examination, it appeared that by using the lastChange parameter, we could retrieve only the stores that had experienced a change within the previous hour. However, a quick test revealed that all active store IDs had undergone a lastChange within the past hour. Hence, considering a follow-up task involving specific store IDs would be unnecessary if all active store IDs are already involved.

The most crucial information to retain about stores is the mapping of storeID to storeName. Other data such as images (banner, logo, and icon) may be deemed irrelevant for our current purposes.

If we were to adopt a star schema approach, the stores table would serve as a dimension table with storeID as the primary key. For simplicity, let's keep the stores table static for this challenge. However, in a more formalized approach, we could implement a mechanism to update the table reactively when a new storeID appears in subsequent API calls to Deals or when a store becomes inactive.

    CREATE TABLE stores (
      store_id SMALLINT,
      store_name VARCHAR(25),
      is_active SMALLINT
    );

DAG: [cheapshark_stores.py](http://url/to/cheapshark_stores.py)

### Deals

Each deal in the API represents the price (and metadata) for a game at a particular store. It's essential to note that even when a game is available at multiple stores, each store's deal entry exists separately. Therefore, if a game is available at three stores, it will have three separate deal entries, one for each store.

For Task 1, which involves calling the API every hour, I initially considered using the sortBy=Recent parameter and checking for lastChange in descending order until encountering a lastChange timestamp over 1 hour old. However, the maxAge parameter simplifies this process by allowing us to filter deals based on their lastChange timestamp within the previous hour directly.

On a more formalized approach, we could maybe think about increasing the maxAge to 2 in order to be sure that we actually get every deal and avoid limit cases if a DAG takes more seconds to start or there's downtime while at the same time a deal got updated. This adjustment would provide a buffer to ensure comprehensive coverage of updated deals and mitigate potential issues related to DAG execution timing and API downtime.

The limitation now lies in the pageSize parameter, which is capped at 60 deals per page. To retrieve all updated deals, we need to loop through the pageNumber, starting from 0, until reaching the maximum page count indicated by the X-Total-Page-Count HTTP header in the response.

If we were to follow a star schema approach, the deals table would serve as our facts table with dealID and last_change as composite primary keys. For simplicity, I generated a DDL based on sample data, with appropriate data types and buffer spaces for potential future expansion.

    CREATE TABLE deals (
      deal_id VARCHAR(100),
      store_id INT,
      game_id INT,
      sale_price DECIMAL(10, 2),
      normal_price DECIMAL(10, 2),
      is_on_sale SMALLINT,
      savings DECIMAL(10, 6),
      deal_rating DECIMAL(3, 1),
      last_change TIMESTAMP
    );

DAG: [cheapshark_deals.py](http://url/to/cheapshark_deals.py)

### Games

In consideration of Tasks 3 and 4, which involve obtaining information about the cheapest and costliest prices ever for games, along with their respective dealIDs and store names, we need to include the cheapestPriceEver in our data model. This information can be retrieved via the Multiple Game Lookup API with up to 25 gameIDs.

It's essential to separate information about deals and games into respective tables. The games table would serve as another dimension table with gameID as the primary key. Additionally, we must insert new records into the table or update existing ones, especially the cheapest_price_ever, which is subject to change in the future.

Release_date and last_change timestamps can benefit from being converted from UNIX timestamps into UTC datetimes. This conversion would facilitate easier interpretation and manipulation of time-related data within the database.

For a more formalized approach, we could utilize an S3 bucket to store raw data as an initial stage and implement sensors as event triggers for subsequent transformation and loading layers. However, due to time constraints, a single DAG with the respective tasks will suffice for now.

    CREATE TABLE games (
      game_id INT,
      internal_name VARCHAR(100),
      title VARCHAR(255),
      metacritic_link VARCHAR(255),
      metacritic_score INT,
      steam_rating_text VARCHAR(50),
      steam_rating_percent INT,
      steam_rating_count INT,
      steam_app_id INT,
      release_date TIMESTAMP,
      thumb VARCHAR(255),
      cheapest_price_ever DECIMAL(10, 2)
    );

![task2](http://url/to/task2.png)

## Task 3

DAG: [task3.sql](http://url/to/task3.sql)

## Task 4

DAG: [task4.sql](http://url/to/task4.sql)

## Task 5
A tipical approach is to use Amazon API Gateway with Amazon SQS (Simple Queue Service), including a Dead Letter Queue (DLQ) to process incomming webhook events, Lambda function for the transformations requiered to store the data into RDS (Relational Database Service) instance.

API Gateway acts as the entry point, receiving API requests and forwarding them to the SQS queue. The SQS queue serves as a buffer, decoupling the API Gateway from downstream processing and providing resilience against fluctuations in request volume. With the inclusion of a Dead Letter Queue (DLQ), failed messages are redirected for analysis and troubleshooting, ensuring the reliability of the system.

A Lambda function subscribed to the SQS queue processes incoming messages asynchronously. This function can perform various tasks before feeding the RDS database. The Lambda function's event-driven architecture enables scalable processing.

The RDS instance serves as the persistent data store, storing processed data securely and reliably.

This architecture follows a "Storage First" pattern, proving beneficial when an application doesn't need extensive data transformation upon receiving API requests. Rather than coupling API Gateway with a Lambda function responsible for parsing, processing, transforming, and storing data, this pattern enables a direct route to an AWS service, such as SQS, via a "service integration." By bypassing the Lambda function, this approach minimizes API call latency, reduces operational costs by eliminating the need for a processing Lambda function, and enhances application reliability by avoiding the introduction of additional code.
Furthermore, additional processing can be executed asynchronously, bolstering application resilience in instances of unavailability in downstream systems

Source: Eric Johnson from AWS, on safeguarding a user's raw data before executing any processing: "Building a serverless URL shortener app without AWS Lambda."

![task6.png](http://url/to/task6.png)
