---
title: Entry paths
---

# Lead-first vs. direct applicants

Lead-first applicants inquired first (a Lead converted into their Contact). Direct, or "stealth", applicants applied with no inquiry on record.

```js
import {originInput, byOrigin, pct} from "./components/origin.js";
const applications = FileAttachment("data/applications.csv").csv({typed: true});
```

```js
const origin = view(originInput());
```

```js
const apps = byOrigin(applications, origin);
const termOrder = d3.sort(d3.groups(apps, (d) => d.term), ([, v]) => v[0].term_order).map(([t]) => t);
const done = apps.filter((d) => !d.is_current_cycle);
const outcomes = d3.rollups(
  done,
  (v) => {
    const decided = v.filter((d) => d.is_admitted || d.is_denied).length;
    const admitted = v.filter((d) => d.is_admitted).length;
    return {
      applicants: v.length,
      submit_rate: v.filter((d) => d.is_submitted).length / v.length,
      admit_rate: decided ? admitted / decided : null,
      yield_rate: admitted ? v.filter((d) => d.is_enrolled).length / admitted : null
    };
  },
  (d) => d.entry_path
).map(([entry_path, s]) => ({entry_path, ...s}));
```

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Applicants by term and entry path</h2>
    ${resize((width) => Plot.plot({
      width,
      height: 300,
      x: {domain: termOrder, label: null},
      y: {grid: true, label: "Applicants"},
      color: {legend: true, domain: ["lead-first", "direct"]},
      marks: [
        Plot.barY(apps, Plot.groupX({y: "count"}, {x: "term", fill: "entry_path", tip: true})),
        Plot.ruleY([0])
      ]
    }))}
  </div>
  <div class="card">
    <h2>Lead-first applicants by lead source</h2>
    ${resize((width) => Plot.plot({
      width,
      height: 300,
      marginLeft: 120,
      x: {grid: true, label: "Applicants"},
      y: {label: null},
      marks: [
        Plot.barX(apps.filter((d) => d.entry_path === "lead-first"),
          Plot.groupY({x: "count"}, {y: (d) => d.lead_source ?? "Unknown", sort: {y: "-x"}, tip: true})),
        Plot.ruleX([0])
      ]
    }))}
  </div>
</div>

<div class="card">
  <h2>Outcomes by entry path, completed terms</h2>
  ${Inputs.table(outcomes, {
    columns: ["entry_path", "applicants", "submit_rate", "admit_rate", "yield_rate"],
    header: {entry_path: "Entry path", applicants: "Applicants", submit_rate: "Submitted", admit_rate: "Admit rate", yield_rate: "Yield"},
    format: {submit_rate: pct, admit_rate: pct, yield_rate: pct}
  })}
</div>

<p class="muted">An applicant who inquired under one email and signed up with another counts as direct here, because the system never linked them. The Data quality page lists those likely duplicates.</p>
