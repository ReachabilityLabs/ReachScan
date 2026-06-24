# Run path — from research question to defensible claim

The [control-surface figure](instrument_control_surface.svg) names the dials. This
is the **procedure** for turning them, in order, so that what you end up with is a
claim you can defend.

```
choose model → choose task → choose projection → choose rigor tier
   → run → inspect receipts → evaluate prediction → decide claim level
```

Each step below says *what you do*, *where it lives*, and *the check that keeps it
honest*.

## 1. Choose the model  (substrate)
Pick the open-weights model and **pin a revision** (a Hugging Face commit SHA).
Lives in the notebook's run-contract cell (`TIER`, `REVISION`).
> Honesty: the model you pick sets *what you're measuring*, not *what you may
> claim* — see the [claim ladder](CLAIM_LADDER.md).

## 2. Choose the task
State the problem and the correct answer. Floor-sum ships as the worked task; for
anything else you supply the prompt and ground truth.
> Honesty: one task is one task — never generality (ladder rung ≤ 2).

## 3. Choose / declare the projection  (the lens)
Decide how raw text becomes an answer, a class, and a target. For a real claim,
use a **projection pack** so the lens is declared, fixture-validated, and hashed:
```bash
reachscan projection validate examples/projections/floor_sum_mod8
```
Build your own lens from the template — see
[`BUILD_A_PROJECTION_PACK.md`](BUILD_A_PROJECTION_PACK.md).
> Honesty: the projection is **locked by hash** once declared. Fixtures must pass
> before the run; an undeclared class fails loud.

## 4. Choose the rigor tier  (targets a claim rung)
Pick the run-contract tier + rigor preset. The run card prints the model,
revision, task, projection, sampler, depth plan, **claim ceiling**, and the
confirmation token; nothing runs until you confirm it.
> Honesty: the tier *targets* a rung on the [claim ladder](CLAIM_LADDER.md); it
> does not grant it. See [`CHOOSE_YOUR_RUN.md`](CHOOSE_YOUR_RUN.md).

## 5. Run
Run the scan (notebook or `reachscan-demo`). It writes `receipts.csv`,
`summary_by_depth.csv`, `run_manifest.json`, and provenance — checkpointed per
depth so a disconnect can resume.
> Honesty: `M` (rollouts/depth) is finite-sample **resolution** — it tightens the
> intervals and decides whether there is enough evidence to avoid `inconclusive`.

## 6. Inspect the receipts  (yield first)
Read the **raw rows** before any conclusion. **Check answer yield first:** if
`ok_answers` at the prompt-only state is low, the extractor isn't catching this
model's format — fix the prompt/projection and rerun. Low yield ≠ low reachability.
Then read the `R_T(f)` trend with Wilson intervals, dominant basin, and entropy.
> Honesty: raw rows are the evidence; the summary is a downstream product. If prose
> and rows disagree, the rows win.

## 7. Evaluate the prediction
If the pack carries a predeclared prediction, compute the verdict from receipts:
```bash
reachscan prediction evaluate <run_dir> --projection <pack_dir>
```
This writes `prediction_verdict.json` (`supported` / `failed` / `inconclusive`) and
records it in the manifest. It refuses a run that used a different pack.
> Honesty: a thin or zero-evidence test is `inconclusive`, never a false support.

## 8. Decide the claim level
Place the run on the [claim ladder](CLAIM_LADDER.md) by what the *design* actually
supports — predeclared? revision-pinned? exposure-audited? replicated? adequate
`M`? — not by the model you used. Write a reproduction note
([template](agents/templates/reproduction_note.md)) stating the rung and what the
run does **not** support.
> Honesty: a `MockSource` run stays at rung 0; one model + one task stays at rung
> ≤ 2; an `inconclusive` verdict cannot be upgraded.

---

The whole path is one idea, restated from the figure: **ReachScan becomes
claim-bearing when the object, sampling conditions, projection lens, and prediction
rule are declared before the run and then evaluated from raw receipts.**
