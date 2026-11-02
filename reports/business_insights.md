# Business Insights

All figures below come from `python -m src.pipeline` run on the UCI Online Retail dataset (transactions from 1 December 2010 to 9 December 2011). The source tables are in `reports/tables/` and the headline numbers are in `reports/summary_metrics.json`. Revenue means `quantity x unit_price` after cleaning, in GBP, net of purchases that were fully reversed by a matching cancellation. It is not profit or contribution margin, because the dataset contains no cost data.

The findings describe associations in historical data. None of them on its own shows that one factor causes another.

## Headline numbers

| Metric | Value |
|---|---|
| Revenue | £8,350,894 |
| Orders | 18,281 |
| Customers | 4,324 |
| Products | 3,646 |
| Countries | 37 |
| Units sold | 4,918,183 |
| Average order value | £456.81 |
| Repeat purchase rate | 65.3% |
| Revenue from repeat customers | 93.5% |
| Median days from first to second order | 51 |

## Answers to the business questions

### Which customer segments generate the most revenue?

Champions (625 customers, 14.5% of the base) generated £4.22M, or 50.6% of revenue. Loyal Customers (793, 18.3%) added £2.33M (27.9%). Together these two segments account for 32.8% of customers and 78.5% of revenue. At Risk is the third-largest segment by revenue: £680K (8.1%) from 573 customers.

### Which segments have declining activity?

Revenue in the last 90 days of the data was compared with the 90 days before that (`rfm_segment_activity_change.csv`):

| Segment | Prior 90 days | Last 90 days | Change |
|---|---|---|---|
| Cannot Lose Them | £72,145 | £21,875 | -69.7% |
| At Risk | £162,121 | £84,488 | -47.9% |
| Hibernating | £72,622 | £43,097 | -40.7% |

Segments come from the same recency data, so part of this decline follows from how the segments are defined: a low recency score means few recent purchases. The table still shows how much revenue these customers used to bring in. Cannot Lose Them customers have a median lifetime revenue of £2,616, which matches Champions (£2,613), but their mean recency is 118 days.

### How much revenue comes from repeat customers?

2,822 of 4,324 customers (65.3%) placed two or more orders. They generated £7.81M, or 93.5% of revenue, and 91.8% of orders. The 1,502 one-time customers generated £541K (6.5%). Median lifetime revenue is £1,131 for returning customers and £253 for one-time customers.

### Which countries contribute most to sales?

The United Kingdom accounts for 82.4% of revenue (£6.88M from 3,909 customers). Netherlands (£283K), EIRE (£248K), Germany (£204K) and France (£182K) are next. The two largest non-UK markets rely on very few accounts: 9 customers in the Netherlands and 3 in EIRE. Germany and France have broader bases of 94 and 87 customers.

### Which products are frequently purchased?

By number of orders: White Hanging Heart T-Light Holder (1,966 orders, 10.8% of all orders), Regency Cakestand 3 Tier (1,664, 9.1%), Jumbo Bag Red Retrospot (1,589, 8.7%), Assorted Colour Bird Ornament (1,372) and Party Bunting (1,369). Regency Cakestand 3 Tier has the highest revenue at £138K. World War 2 Gliders Asstd Designs sells the most units (54,175).

## Further observations

- **Revenue trend.** Monthly revenue stayed between £439K and £652K from January to August 2011. It then rose to £928K in September, £969K in October and £1.12M in November. September to November make up 36.2% of total revenue. The data covers only one year, so it cannot confirm whether this is a repeating seasonal pattern. December 2011 is partial, covering 1 to 9 December.
- **Concentration.** The top 1% of customers (43) account for 30.1% of revenue. The top 10% (432) account for 60.1%, and the top 20% (865) for 73.8%. The largest single customer contributes 3.3%.
- **Acquisition.** New customers per month fell from 414 in January 2011 to 169 in August 2011, then recovered to 296 to 356 in September to November. The share of active customers who are returning rose from 44% to 81% over the year. Part of that rise is mechanical, because the pool of earlier customers grows over time.
- **Retention.** For cohorts acquired in 2011, between 14.6% and 23.6% ordered again in the month after their first purchase. Across all cohorts, 23.5% of eligible customers ordered in month 1. The December 2010 cohort keeps 32% to 40% active every month. That cohort probably includes long-standing customers whose earlier purchases fall before the data starts.
- **Time to second order.** Among customers who placed a second order, 25% did so within 20 days, 50% within 51 days and 75% within 112 days.
- **Cancellations.** 8,872 cancellation lines worth £608,689 were removed. 2,761 purchase lines were fully reversed by an identical cancellation, including single orders of more than 74,000 and 80,000 units.

## Recommendations

1. **Protect the Champions and Loyal Customers.** These 1,418 customers produce 78.5% of revenue. Track their order frequency every month and treat a fall in frequency as an early warning. Retention spend aimed at this group covers most of the revenue at stake.
2. **Run a targeted win-back for Cannot Lose Them and At Risk.** These 658 customers generated £935K in total but are now buying much less. Contact the 85 Cannot Lose Them customers individually, since their median lifetime revenue matches Champions. Measure any campaign against a holdout group, because the observed decline does not show what would bring them back.
3. **Focus on the second order.** A third of customers never order again, and the median repeat buyer returns after 51 days. A follow-up contact within roughly 50 days of the first order, tested with an A/B design, addresses the step where most customers are lost.
4. **Manage revenue concentration risk.** With 30.1% of revenue coming from 43 customers, losing one large account would show up clearly in monthly revenue. Assign the top 1% to account management and monitor their order intervals.
5. **Broaden international markets.** Revenue in the Netherlands and EIRE depends on 12 customers. Germany and France already have about 90 customers each, which gives a better base for testing growth. Expansion results should be measured by country.
6. **Prepare for the September to November peak.** The last observed autumn produced 36% of annual revenue. Plan stock for the most frequently ordered products early, and check whether the pattern repeats once more years of data are available.
7. **Investigate large cancellations.** £608K of cancellations and fully reversed bulk orders distort revenue reporting. Reviewing why very large orders are cancelled could protect revenue and improve forecasting.
