2026-02-25 09:51


**Just at a high level more carrot drop downs is probably better and I trust your judgement**

# Project Overview
Right now Capacity MW is a field where you can enter any number.

The CTCC has sub sets of CT X AC/DC that determine
- What Capacity can be chosen 
- What conductor type is an option

For example capacities:
- An overhead, DC, line could have a capacity:
	- 500MW,  1500MW, 2000MW, 2400MW, or 6000MW
- An underground, AC, line could have a capacity: 
	- 140MW, 329MW, 394MW, 460MW, 657MW, 1792MW, 2598MW, 6625MW

For example conductor types:
- An overhead line (regardless of AC or DC):
	- Standard Aluminum Conductor or Advanced Aluminum Conductor
- An underground line (regardless of AC or DC):
	- Underground Copper Conductor 
- A subsea line (regardless of AC or DC):
	- Subsea Copper Conductor

--- 

Could the reconductoring and uses existing ROW be by themselves?

---


The Greenfield Comparison fields (capacity and conductor type) should only appear if some switch is flipped. They provide an optional calculation that I dont think we even report in results right now:

Greenfield comparison capacity (MW) and greenfield comparison conductor type are optional inputs used only for greenfield (non‑reconductoring) projects. They define an alternative design so the line loss module can compare it to your primary design (the one defined by capacity_mw and conductor_type).

When both are set (non‑null and comparison capacity ≠ 0), line_loss_costs.py runs an extra analysis that computes:

1. Primary configuration: your actual project (primary capacity + primary conductor).

2. Comparison configuration: the alternative (comparison capacity + comparison conductor).

3. Counterfactual: primary conductor at comparison capacity (to isolate conductor choice at the same capacity).

It then reports three comparison methods (direct, counterfactual, normalized) with loss differences and NPVs in the printed/console output.


--- 


# Physical Route Details
Can terrain multipliers be like hidden? SOmething where you can see terrain multipliers as a drop down, if you hit the drop down then you would see all the multipliers and could modify them

Need to have the sum of the routes miles



# Financial Parameters
Base year comes first (get rid of comma)

Also we need to display the real WACC. It is calculated by the CTCC.

We should probably get rid of capital structure and just rely on the WACC nominal. The CTCC's current logic is to default to WACC nominal if a capital structure isn't provided. So if one is provided it will ignore WACC nominal.


Everything from AFUDC -> Construction Insurance timing should be its own tab, labeled something like "Regulated Rate of Return" or "Revenue Requirements"

The cost timing patterns need to sum = 1.



# Primary BCR
**I think primary BCR should be its own tab**
Probably a tab in the results section. 

# Operational Costs
Should be earlier in the input tabs. It should only display the relevant construction type and terrains.


I think that Wildfire Liability Insurance should be moved to Risk Costs 


# Risk Parameters
Should probably be titled "Risk Costs" or "Costs Associated With Risk"

User should not be able to choose a discount rate on this tab. It should always use social discount rate. It is totally fine for the social discount rate defined in the Financial parameters tab to appear in this tab so long as it can't be edited.

Any terrains that the route doesn't cross don't need to be displayed.

# Environmental Mitigation
Should probably have two "sub tabs"? Since the base cost is conceptually different than credits for habitat destruction.



# Emissions 
Emissions intensities should be the last thing and not the main thing for users to tweak. Users should mostly change the fuel mix and if they want the social costs of the pollutants.


# Congestion and Curtailment
Get rid of near binding hours and near average exceedance and near binding relief factor, and get rid of value of lost load.

Since the user can select if its a reconductoring project or not whichever configuration is correct should determine if its greenfield congestion and curtailment reductions or reconductoring congestion and curtailment reductions