/*
## Task 4
Create a query that shows when a `Deal` is not available anymore or when a `Deal` is not on sale anymore.
*/

/*
Considerations:
Based on the API creator's previous awnser: "The only reason a dealID would go away would be if a Product was removed (or changed name) at a Store". 
Based on that, the only way to check if a deal is still available is to call the deals?id= to the respective dealId and checking if there's a response back. 
There isn't a scalable solution to keep it cached since the dealIds will linearly increase every hour. 
*/

SELECT
    d.deal_id,
    CASE
        WHEN d.is_on_sale = 0 THEN 'Deal is no longer on sale'
        ELSE 'Deal is on sale'
    END AS deal_status
FROM
    deals d
