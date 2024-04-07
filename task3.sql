/*
## Task 3
Create a query that shows how much has the price of a game increased in comparison to its `cheaper price ever` and its `costlier price ever`. 
The query must show the price increase in %, the name of the game, dealId of the costlier price ever and the name of the store of that deal.
*/

/*
Considerations:
We must consider the cases where the costlier deal price ever is the same amongst stores and deals.
The output should list the costliest_deal_ids and costliest_store_names if that's the case.
*/

WITH costliest_deals AS (
  SELECT
    d.game_id,
    LISTAGG(d.deal_id, ',') WITHIN GROUP (ORDER BY d.deal_id) AS costliest_deal_ids,
    LISTAGG(s.store_name, ',') WITHIN GROUP (ORDER BY d.deal_id) AS costliest_store_names,
    d.sale_price AS costliest_price_ever
  FROM
    deals d
  JOIN (
    SELECT
      game_id,
      MAX(sale_price) AS costliest_price_ever
    FROM
      deals
    GROUP BY
      game_id
  ) c ON d.game_id = c.game_id AND d.sale_price = c.costliest_price_ever
  JOIN stores s ON d.store_id = s.store_id
  GROUP BY
    d.game_id, d.sale_price
),
cheapest_prices AS (
  SELECT
    g.game_id,
    g.title,
    g.cheapest_price_ever
  FROM
    games g
)
SELECT
  cp.title AS game_title,
  cp.cheapest_price_ever,
  cd.costliest_price_ever,
  cd.costliest_deal_ids AS costliest_deal_ids,
  cd.costliest_store_names AS costliest_store_names,
  ((cd.costliest_price_ever - cp.cheapest_price_ever) / cp.cheapest_price_ever) * 100 AS price_increase_percentage
FROM
  cheapest_prices cp
JOIN
  costliest_deals cd ON cp.game_id = cd.game_id;
