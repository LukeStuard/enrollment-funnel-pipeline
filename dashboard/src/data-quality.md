---
title: Data quality
---

# Data quality

These are known issues, not pipeline failures. dbt tests flag them as warnings on every build, and the same rules feed this page.

```js
const issues = FileAttachment("data/dq_issues.csv").csv({typed: true});
```

```js
const checkLabel = {
  likely_duplicate_person: "Likely duplicate person",
  missing_program_interest: "Inquiry with no program",
  missing_submitted_date: "Submitted with no date"
};
const labeled = issues.map((d) => ({...d, check: checkLabel[d.check_name] ?? d.check_name}));
```

```js
display(html`<div class="grid grid-cols-3">${Object.entries(checkLabel).map(([k, label]) => html`<div class="card"><h2>${label}</h2><span class="big">${issues.filter((d) => d.check_name === k).length}</span></div>`)}</div>`);
```

<div class="card">
  <h2>Flagged records by check and source system</h2>
  ${resize((width) => Plot.plot({
    width,
    height: 200,
    marginLeft: 170,
    x: {grid: true, label: "Records"},
    y: {label: null},
    color: {legend: true, domain: ["salesforce", "archive"]},
    marks: [
      Plot.barX(labeled, Plot.groupY({x: "count"}, {y: "check", fill: "source_system", tip: true})),
      Plot.ruleX([0])
    ]
  }))}
</div>

**Likely duplicate person:** an inquiry (Lead) and an applicant (Contact) with the same name and phone that were never linked, because the applicant signed up with a different email than they inquired with. The conversion trigger matches on email, so it can't merge them. **Inquiry with no program:** the inquiry form allowed a blank program. **Submitted with no date:** status moved past Draft without the submitted date being set; the funnel falls back to the stage history for these.

```js
const search = view(Inputs.search(labeled, {placeholder: "Search flagged records"}));
```

<div class="card">
  ${Inputs.table(search, {
    columns: ["check", "source_system", "origin", "term", "record_id", "detail"],
    header: {check: "Check", source_system: "Source", origin: "Origin", term: "Term", record_id: "Record", detail: "Detail"},
    rows: 15
  })}
</div>
