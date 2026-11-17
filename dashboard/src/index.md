---
title: Funnel overview
---

# Enrollment funnel

```js
import {originInput, byOrigin, pct} from "./components/origin.js";
const funnel = FileAttachment("data/funnel.csv").csv({typed: true});
const meta = FileAttachment("data/meta.json").json();
```

```js
const origin = view(originInput());
```

```js
const rows = byOrigin(funnel, origin);
const terms = d3.rollups(
  rows,
  (v) => ({
    term_order: v[0].term_order,
    current: v[0].is_current_cycle,
    inquiries: d3.sum(v, (d) => d.inquiries),
    applicants: d3.sum(v, (d) => d.applicants),
    lead_first: d3.sum(v, (d) => d.lead_first_applicants),
    submitted: d3.sum(v, (d) => d.submitted),
    admitted: d3.sum(v, (d) => d.admitted),
    denied: d3.sum(v, (d) => d.denied),
    enrolled: d3.sum(v, (d) => d.enrolled)
  }),
  (d) => d.term
).map(([term, s]) => ({term, ...s})).sort((a, b) => a.term_order - b.term_order);
const termOrder = terms.map((d) => d.term);
const done = terms.filter((d) => !d.current);
const inFlight = terms.filter((d) => d.current);
const sum = (v, k) => d3.sum(v, (d) => d[k]);
```

<div class="grid grid-cols-4">
  <div class="card">
    <h2>Applicants, completed terms</h2>
    <span class="big">${sum(done, "applicants").toLocaleString("en-US")}</span>
  </div>
  <div class="card">
    <h2>Admit rate</h2>
    <span class="big">${pct(sum(done, "admitted") / (sum(done, "admitted") + sum(done, "denied")))}</span>
    <span class="muted">admitted / decided</span>
  </div>
  <div class="card">
    <h2>Yield</h2>
    <span class="big">${pct(sum(done, "enrolled") / sum(done, "admitted"))}</span>
    <span class="muted">enrolled / admitted</span>
  </div>
  <div class="card">
    <h2>Current cycle, in flight</h2>
    <span class="big">${sum(inFlight, "applicants").toLocaleString("en-US")}</span>
    <span class="muted">applicants for ${inFlight.map((d) => d.term).join(", ") || "no open terms"}</span>
  </div>
</div>

```js
const stages = ["inquiries", "applicants", "submitted", "admitted", "enrolled"];
const stageLabel = {inquiries: "Inquiries", applicants: "Applicants", submitted: "Submitted", admitted: "Admitted", enrolled: "Enrolled"};
const long = terms.flatMap((t) => stages.map((s) => ({term: t.term, stage: stageLabel[s], count: t[s]})));
```

<div class="card">
  <h2>Funnel by term</h2>
  <h3>Current-cycle terms are still in flight, so their later stages are still filling in.</h3>
  ${resize((width) => Plot.plot({
    width,
    height: 340,
    fx: {domain: termOrder, label: null},
    x: {domain: stages.map((s) => stageLabel[s]), axis: null},
    y: {grid: true, label: "Records"},
    color: {domain: stages.map((s) => stageLabel[s]), legend: true},
    marks: [
      Plot.barY(long, {fx: "term", x: "stage", y: "count", fill: "stage", tip: true}),
      Plot.ruleY([0])
    ]
  }))}
</div>

```js
const rates = terms.flatMap((t) => [
  {term: t.term, rate: "Inquiry to applicant (lead-first)", value: t.inquiries ? t.lead_first / t.inquiries : null},
  {term: t.term, rate: "Admit rate", value: t.admitted + t.denied ? t.admitted / (t.admitted + t.denied) : null},
  {term: t.term, rate: "Yield", value: t.admitted ? t.enrolled / t.admitted : null}
]).filter((d) => d.value != null);
```

<div class="card">
  <h2>Conversion rates by term</h2>
  ${resize((width) => Plot.plot({
    width,
    height: 300,
    x: {domain: termOrder, label: null},
    y: {domain: [0, 1], tickFormat: "%", grid: true, label: "Rate"},
    color: {legend: true},
    marks: [
      Plot.lineY(rates, {x: "term", y: "value", stroke: "rate", marker: true, tip: true}),
      Plot.ruleY([0])
    ]
  }))}
</div>

<p class="muted">Data pulled ${meta.built_at}. Inquiry-to-applicant counts only applicants who entered as a Lead; most applicants apply directly.</p>
