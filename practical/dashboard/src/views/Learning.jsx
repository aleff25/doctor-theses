import Expandable from '../ui/Expandable'
import { formatValue, useData } from '../data/DataContext'

function pct(value) {
  return value === null || value === undefined ? 'n/d' : value.toFixed(2)
}

/**
 * Stage 4, reported the way its own design decisions demand.
 *
 * No headline average across folds: with three systems and single-digit
 * positives, an average would flatter the result into meaninglessness. Each
 * fold is shown with its own positive count and the majority-class rate beside
 * it, so a model that looks excellent while learning nothing is visible as
 * such.
 */
export default function Learning() {
  const { data } = useData()
  const learning = data.learning

  if (!learning.available) {
    return (
      <>
        <h1>Learning</h1>
        <div className="note warn">{learning.reason}</div>
      </>
    )
  }

  return (
    <>
      <h1>Supervision and the first baseline</h1>
      <p className="lede">
        The labels are synthetic by construction: three operators mutate an architecture model and
        record what they damaged. What follows shows whether the metrics respond to an injected
        architectural change. It says nothing about whether they predict real-world quality
        outcomes, and no amount of tuning would change that (DD-008).
      </p>

      <div className="note stop">
        <strong>Read every number on this page as a wiring test.</strong> Mutants are not drawn from
        the distribution of real architectural decay, so results transfer to "does the metric detect
        this property", never to "does this predict failure". That sentence belongs in threats to
        validity whether or not the numbers improve.
      </div>

      {learning.tasks.map((task) => (
        <Expandable
          key={task.task}
          title={<span className="mono">{task.task}</span>}
          defaultOpen={Boolean(task.run)}
          subtitle={`${task.rows} rows · ${task.positives} positive`}
          badges={
            <span className="badges">
              {task.systems.map((system) => (
                <span key={system} className="chip">
                  {system}
                </span>
              ))}
              {task.systems.length < 2 ? (
                <span className="chip stop">no leave-one-system-out possible</span>
              ) : null}
            </span>
          }
        >
          <div className="badges">
            <span className="chip">{task.variants.length} variants</span>
            <span className="chip">{task.features.length} features</span>
            {task.unverified_negatives > 0 ? (
              <span className="chip warn">
                {task.unverified_negatives} unverified negatives
              </span>
            ) : null}
          </div>

          {task.run ? (
            <>
              <div className="section-label">Features excluded, and why</div>
              <div className="note accent small">
                <span className="mono">{task.run.excluded_features.join(', ')}</span> are withheld
                from this task. The deterministic detector of the injected property would predict it
                perfectly and prove nothing, and a system-level metric would act as a system
                identifier under a leave-one-system-out split.
              </div>
            </>
          ) : null}

          <div className="section-label">Features used</div>
          <p className="badges">
            {task.features.map((feature) => (
              <span key={feature} className="chip mono">
                {feature}
              </span>
            ))}
          </p>

          {task.run ? (
            <>
              <div className="section-label">
                Leave-one-system-out · {task.run.model_version}
              </div>
              <div className="scroll-x">
                <table>
                  <thead>
                    <tr>
                      <th>Held out</th>
                      <th className="num">n</th>
                      <th className="num">Positives</th>
                      <th className="num">Majority</th>
                      <th className="num">Recall</th>
                      <th className="num">Precision</th>
                      <th className="num">ROC AUC</th>
                    </tr>
                  </thead>
                  <tbody>
                    {task.run.folds.map((fold) => (
                      <tr key={fold.held_out_system}>
                        <td className="mono">{fold.held_out_system}</td>
                        <td className="num">{fold.n}</td>
                        <td className="num">{fold.positives}</td>
                        <td className="num">{pct(fold.majority_rate)}</td>
                        <td className="num">{pct(fold.recall)}</td>
                        <td className="num">{pct(fold.precision)}</td>
                        <td className="num">{pct(fold.roc_auc)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="small muted">
                Majority is the share of the held-out fold taken by its larger class: a model that
                answered "no" every time would score that. Compare each fold against its own
                majority, never against the other folds.
              </p>

              {task.prediction_examples.map((fold) => (
                <div key={fold.held_out_system}>
                  <div className="section-label">
                    Attributions · {fold.held_out_system} held out
                  </div>
                  {fold.examples.map((example) => (
                    <div key={example.element_id} className="card" style={{ marginBottom: 8 }}>
                      <div className="badges">
                        <span className="chip mono">{example.element_id}</span>
                        <span className={`chip ${example.prediction.truth === 1 ? 'stop' : ''}`}>
                          truth {example.prediction.truth}
                        </span>
                        <span className="chip">predicted {example.prediction.label}</span>
                        <span className="chip mono">
                          score {formatValue(example.prediction.score)}
                        </span>
                      </div>
                      <div className="scroll-x">
                        <table>
                          <thead>
                            <tr>
                              <th>Feature</th>
                              <th>Kind</th>
                              <th className="num">Contribution</th>
                            </tr>
                          </thead>
                          <tbody>
                            {example.attributions.map((attribution) => (
                              <tr key={attribution.feature}>
                                <td className="mono">{attribution.feature}</td>
                                <td className="small muted">{attribution.kind}</td>
                                <td className="num">
                                  {attribution.contribution > 0 ? '+' : ''}
                                  {attribution.contribution.toFixed(3)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <p className="small muted" style={{ marginBottom: 0 }}>
                        Exact, not estimated: for a linear model the contribution of a feature is
                        its coefficient times its standardised value. Every row names a metric and
                        an architectural element, which is what the stage 4 to 5 contract requires.
                      </p>
                    </div>
                  ))}
                </div>
              ))}
            </>
          ) : (
            <div className="note warn small">
              No training run for this task. With labels in{' '}
              {task.systems.length === 1 ? 'a single system' : 'too few systems'}, a
              leave-one-system-out split has no fold, and a random split is not offered on purpose
              (P2). That is a finding about the label source, not a reason to change the splitter.
            </div>
          )}
        </Expandable>
      ))}
    </>
  )
}
