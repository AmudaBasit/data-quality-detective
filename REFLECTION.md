# Artifact 4 · Reflection

The pass rate was easy to report and easy to misread. It reached 100% because I repaired some rows and excluded others. Keeping the source files and a decision log made the result easier to explain. It also showed which transactions would be missing from any analysis using the cleaned data.

I chose to quarantine missing prices and regions because a guessed value could change a revenue total or a regional comparison. I standardized category spelling and alternate dates because those repairs preserve the original meaning. The simulated defects occur early in the timeline, so dropping them can distort comparisons by date. With operational data, I would measure exclusion rates by day and source system and investigate the feed before relying on any historical trend.

The return prediction exercise showed why feature availability matters. A positive refund was an exact indicator of a return in this synthetic example. Including it in a checkout model would make the evaluation misleading. A chronological split and features available at checkout give a more realistic starting point. The smaller regional cohort and the artificial return pattern still limit what can be inferred about model performance in a real store.

I used fully synthetic records so I could share the raw examples and explain the whole workflow publicly. With real data, I would keep quarantine exports access-controlled and review whether a combination of otherwise ordinary fields could identify someone.
