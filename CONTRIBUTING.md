# Contributing to reachscan

Thank you for your interest. `reachscan` is a small, deliberately lean measurement
instrument, not a platform. The most valuable thing you can do with it is often
*not* to change it — so this guide is as much about **where different kinds of work
belong** as it is about mechanics.

Please read the short distinction in [Two ways to contribute](#two-ways-to-contribute)
before opening anything; it will save us both time.

## Two ways to contribute

There is an important difference between **improving the instrument** and **building
with the instrument**, and they have different homes.

### 1. Improving the instrument → here, via a Pull Request

Changes to `reachscan` itself belong in this repository:

- Bug fixes in the engine, sources, or readout.
- A new, generally useful model **source** (alongside the existing mock and HuggingFace paths).
- Documentation corrections and clarifications.
- Tests that strengthen the existing guarantees.

These go through the normal review flow (see [Mechanics](#mechanics)). The core is
intentionally small and dependency-light; please keep it that way. Changes that add
heavy dependencies, broaden scope, or trade rigor for convenience will usually be
declined — open an Issue to discuss before writing code for anything non-trivial.

### 2. Building with the instrument → your own work, that cites this one

If you used `reachscan` to design your **own task, Projection, or control surface**,
ran it, and got data back — congratulations, that result is **yours**. It does not
need to live in this repository, and as a rule it shouldn't:

- **Your run data stays in your deposit.** Large result sets bloat the repo and,
  more importantly, they are your contribution, not ours. Deposit them somewhere
  citable (Zenodo, OSF, your own repo) and **cite reachscan** (see `CITATION.cff`
  or the *Citation* section of the README). That citation *is* the bridge — it is
  how downstream work connects back without being absorbed.
- **Want to show people what you built?** Open a thread in
  [Discussions](../../discussions) (if enabled) rather than a Pull Request. A
  "here's a Projection I built and what I found" post is welcome and is exactly the
  kind of thing this instrument exists to enable.
- **Built a Projection you think is broadly reusable?** Open an Issue describing it
  first. If it generalizes cleanly, we can talk about a small `examples/` or
  `contrib/` entry. Most community Projections are better off in your own repo,
  linked from a Discussion.

The healthy growth model for a research instrument is **citation, not accumulation**:
the core stays sharp, and an ecosystem of independent work points back at it.

## Reporting bugs and asking questions

Open an [Issue](../../issues). A good report includes:

- What you ran (command, source/model, Projection if any).
- What you expected and what happened.
- The relevant **raw artifacts** if you can share them — `run_manifest.json` and
  `summary_by_depth.csv` are usually enough. Per this project's norms, raw artifacts
  are authoritative; pasted prose summaries are not.

## Mechanics (how a Pull Request works)

If you've never sent one: GitHub's flow is fork → branch → pull request.

1. **Fork** this repository (creates your own copy) and clone your fork.
2. Create a branch: `git checkout -b fix/short-description`.
3. Make your change. Keep the diff focused — one concern per PR.
4. Set up and run the tests:
   ```bash
   pip install -e ".[test]"
   pytest
   ```
   CI runs the same suite; a green checkmark is expected before review.
5. Commit with a clear message describing *why*, not just *what*.
6. Push to your fork and open a **Pull Request** against `main`. Describe the change
   and link any related Issue.

The maintainer reviews every PR and decides whether to merge. Nothing enters the
repository without that review — so don't hesitate to propose; the gate is real and
on our side.

## Norms this project holds itself to

These are not bureaucracy; they are the reason the instrument is trustworthy. Changes
are expected to respect them:

- **No overclaiming.** A mock run is a fixture, not a result. Reproductions show the
  *shape* of a finding unless run under the documented contract. Language in code,
  docs, and outputs should never imply more than was measured.
- **Provenance is preserved.** Artifacts carry their manifest and seed rules. Don't
  add code paths that produce results without recording how they were produced.
- **Raw artifacts are authoritative; generated prose is provisional.** If a change
  touches the readout, the underlying CSV/JSON must remain the source of truth.

## License

By contributing, you agree that your contributions are licensed under the project's
[Apache-2.0](LICENSE) license.
