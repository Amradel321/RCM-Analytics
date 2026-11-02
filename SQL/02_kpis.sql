-- Headline KPIs

Select Count(*) As Claim_Lines,
       SUM(carc_code IS NOT NULL) AS initial_denied_lines,
	   Sum(claim_status != 'Paid') As Unresolved_Denied_lines,
       Round((Sum(carc_code IS NOT NULL)/ count(*))*100,2) As Denial_rate_pct,
      Round( (sum(is_first_pass_paid) / Count(*))*100,2) As first_pass_pct,
      Round((sum( claim_status ='Paid' and carc_code IS NOT NULL) / sum( carc_code IS NOT NULL)) *100,2) As recovery_rate_pct
From fact_claim_line;  


-- Denial rate by payer
Select payer_name, Round((Sum(carc_code is not null) / count(*))*100,1) as Denial_rate_pct
from fact_claim_line AS FCL
Join dim_payer AS DP
On FCL.payer_key = DP.payer_key
group by payer_name
order by Denial_rate_pct DESC;





-- Denials by category, with dollars
Select denial_category, FCL.carc_code, `description`,
 Sum(FCL.carc_code is not null and claim_status!='paid' ) AS Denied_lines,
 Sum(Case When claim_status!='paid' Then billed_amount Else 0 END) as billed_amount
from fact_claim_line AS FCL
Join dim_denial_code AS DDC
On FCL.carc_code = DDC.carc_code
group by denial_category, carc_code, `description`
order by billed_amount desc;



-- Avg days untill payment
Select payer_name, Round(Avg(Datediff(DP.full_date, DS.full_date)),0) AS Avg_days_to_payment
From fact_claim_line As FCL
Join dim_payer AS P On FCl.payer_key = P.payer_key
Join dim_date AS DS On FCL.submit_date_key = DS.date_key
Join dim_date AS DP On FCL.payment_date_key = DP.date_key
where is_first_pass_paid = 1
group by payer_name
order by Avg_days_to_payment DESC;












-- AR aging
Select CASE WHEN Days <= 30 THEN '0-30' WHEN Days <= 60 THEN '31-60'
            WHEN Days <= 90 THEN '61-90' WHEN Days <= 120 THEN '91-120'
            ELSE '120+' END AS bucket
		, count(claim_line_id), sum(billed_amount)
From(
Select claim_id,claim_line_id, billed_amount, datediff('2026-09-30', DS.full_date) As Days
From fact_claim_line As FCL
Join dim_date AS DS
 On FCL.submit_date_key = DS.date_key
where claim_status  NOT IN ('Paid', 'Written-off')) As T
group by bucket
order by  min(days)
;





