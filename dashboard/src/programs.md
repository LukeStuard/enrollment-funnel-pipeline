---
title: Programs
---

# Conversion by program

```js
import {originInput, byOrigin, pct} from "./components/origin.js";
const funnel = FileAttachment("data/funnel.csv").csv({typed: true});
```

```js
const origin = view(originInput());
```

```js
const rows = byOrigin(funnel, origin).filter((d) => !d.is_current_cycle && d.program !== "Unknown");
const programs = d3.rollups(
  rows,
  (v) => {
    const admitted = d3.sum(v, (d) => d.admitted);
    const denied = d3.sum(v, (d) => d.denied);
    const enrolled = d3.sum(v, (d) => d.enrolled);
    return {
      applicants: d3.sum(v, (d) => d.applicants),
      admitted,
      enrolled,
      admit_rate: admitted + denied ? admitted / (admitted + denied) : null,
      yield_rate: admitted ? enrolled / admitted : null
    };
  },
  (d) => d.program
).map(([program, s]) => ({program, ...s})).sort((a, b) => b.applicants - a.applicants);
const long = programs.flatMap((p) => [
  {program: p.program, measure: "Admit rate", value: p.admit_rate},
  {program: p.program, measure: "Yield", value: p.yield_rate}
]);
```

<div class="card">
  <h2>Admit rate and yield by program</h2>
  <h3>Completed terms only.</h3>
  ${resize((width) => Plot.plot({
    width,
    height: 260,
    marginLeft: 170,
    x: {domain: [0, 1], tickFormat: "%", grid: true, label: "Rate"},
    y: {label: null, domain: programs.map((p) => p.program)},
    fy: {label: null},
    color: {legend: true},
    marks: [
      Plot.barX(long, {x: "value", y: "program", fy: "measure", fill: "measure", tip: true}),
      Plot.ruleX([0])
    ]
  }))}
</div>

<div class="card">
  ${Inputs.table(programs, {
    columns: ["program", "applicants", "admitted", "enrolled", "admit_rate", "yield_rate"],
    header: {program: "Program", applicants: "Applicants", admitted: "Admitted", enrolled: "Enrolled", admit_rate: "Admit rate", yield_rate: "Yield"},
    format: {admit_rate: pct, yield_rate: pct}
  })}
</div>
