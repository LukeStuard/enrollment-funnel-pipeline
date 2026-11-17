---
title: Time between stages
---

# Time between stages

```js
import {originInput, byOrigin} from "./components/origin.js";
const applications = FileAttachment("data/applications.csv").csv({typed: true});
```

```js
const origin = view(originInput());
```

```js
const apps = byOrigin(applications, origin);
const steps = [
  {key: "days_inquiry_to_apply", label: "Inquiry to application (lead-first only)"},
  {key: "days_apply_to_submit", label: "Application to submission"},
  {key: "days_submit_to_decision", label: "Submission to decision"}
];
const long = steps.flatMap((s) =>
  apps.filter((d) => d[s.key] != null).map((d) => ({step: s.label, program: d.program, days: d[s.key]}))
);
const medians = d3.rollups(long, (v) => d3.median(v, (d) => d.days), (d) => d.step);
```

```js
display(html`<div class="grid grid-cols-3">${medians.map(([step, m]) => html`<div class="card"><h2>${step}</h2><span class="big">${m} days</span> <span class="muted">median</span></div>`)}</div>`);
```

<div class="card">
  <h2>Days between stages by program</h2>
  <h3>Boxes show the middle half of applications; whiskers the typical range; dots outliers.</h3>
  ${resize((width) => Plot.plot({
    width,
    height: 520,
    marginLeft: 170,
    marginRight: 200,
    x: {grid: true, label: "Days"},
    y: {label: null},
    fy: {label: null, domain: steps.map((s) => s.label)},
    marks: [Plot.boxX(long, {x: "days", y: "program", fy: "step"})]
  }))}
</div>
