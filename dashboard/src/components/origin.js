import * as Inputs from "npm:@observablehq/inputs";

// The shared "which records" toggle. Demo records are applications the
// gateway and intake projects created in the same Salesforce org.
export function originInput() {
  return Inputs.radio(
    new Map([
      ["Synthetic data set", "generator"],
      ["Include demo records", "all"]
    ]),
    {value: "generator", label: "Records"}
  );
}

export function byOrigin(rows, choice) {
  return choice === "all" ? rows : rows.filter((d) => d.origin === "generator");
}

export const pct = (x) => (x == null || Number.isNaN(x) ? "–" : `${(x * 100).toFixed(0)}%`);
