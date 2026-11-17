// See https://observablehq.com/framework/config for documentation.
export default {
  title: "Enrollment Funnel",

  pages: [
    {name: "Funnel overview", path: "/"},
    {name: "Programs", path: "/programs"},
    {name: "Entry paths", path: "/entry-paths"},
    {name: "Time between stages", path: "/timing"},
    {name: "Data quality", path: "/data-quality"}
  ],

  root: "src",
  theme: "dashboard",
  toc: false,
  pager: false,
  footer: "Synthetic data. Built with Observable Framework from dbt marts in MotherDuck.",

  // Run Python data loaders with the active environment's `python` (the
  // project venv locally, setup-python in CI) instead of the default `python3`,
  // which on Windows can resolve to the Microsoft Store stub.
  interpreters: {
    ".py": ["python"]
  }
};
