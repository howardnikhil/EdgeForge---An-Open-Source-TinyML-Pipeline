/**
 * Canonical Metric Formatter & Utilities for EdgeForge.
 *
 * Ensures consistent, task-aware experiment metric handling, labels, and chart values
 * across ProjectDashboard, ExperimentsPage, TrainingPage, tables, tooltips, and cards.
 */

export type TaskType = 'classification' | 'regression';

export interface FormattedMetric {
  taskType: TaskType;
  label: string;          // e.g. "Test Accuracy" or "Test R²"
  shortLabel: string;     // e.g. "Accuracy" or "R²"
  value: string;          // e.g. "96.23%" or "R² 0.842" or "—"
  plainValue: string;     // e.g. "96.23%" or "0.842"
  raw: number | null;     // Raw float metric (e.g. 0.9623 or 0.842)
  cvValue: string;        // e.g. "94.7% ± 2.1%" or "0.801 ± 0.044"
  secondaryLabel?: string;// "F1 Score" or "RMSE"
  secondaryValue?: string;// "0.958" or "2.130"
}

export interface ChartMetricPoint {
  name: string;
  algorithm: string;
  score: number;
  displayValue: string;
  size: number;
  taskType: TaskType;
  rawScore: number;
}

/**
 * Detect the task type of an experiment from its task_type field or metrics structure.
 */
export function detectTaskType(exp: any): TaskType {
  if (exp?.task_type === 'regression' || exp?.task_type === 'classification') {
    return exp.task_type;
  }
  if (exp?.config?.task_type === 'regression' || exp?.config?.task_type === 'classification') {
    return exp.config.task_type;
  }
  const m = exp?.metrics;
  if (m) {
    if (m.r2 !== undefined || m.r2_score !== undefined || m.test_r2 !== undefined || m.train_r2 !== undefined) {
      return 'regression';
    }
    if (m.accuracy !== undefined || m.test_accuracy !== undefined || m.train_accuracy !== undefined) {
      return 'classification';
    }
  }
  return 'classification';
}

/**
 * Format classification accuracy value into percentage representation.
 * E.g., 0.9623 -> "96.23%", 1.0 -> "100.00%".
 */
export function formatAccuracy(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val) || !isFinite(val)) return '—';
  const pct = val > 1.0 ? val : val * 100.0;
  return `${pct.toFixed(2)}%`;
}

/**
 * Format regression R² value into raw numeric representation with 3 decimal places.
 * E.g., 0.842 -> "0.842", -1.643 -> "-1.643", 1.0 -> "1.000".
 * NEVER multiplies by 100 and NEVER appends %.
 */
export function formatR2(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val) || !isFinite(val)) return '—';
  return val.toFixed(3);
}

/**
 * Format an experiment's primary metrics into a canonical FormattedMetric structure.
 */
export function formatExperimentMetric(exp: any): FormattedMetric {
  const taskType = detectTaskType(exp);
  const m = exp?.metrics || {};

  if (taskType === 'regression') {
    const rawR2 = m.test_r2 ?? m.r2 ?? m.r2_score ?? null;
    const isValidR2 = rawR2 !== null && rawR2 !== undefined && !isNaN(rawR2) && isFinite(rawR2);
    const plainR2Str = isValidR2 ? formatR2(rawR2) : '—';

    let cvStr = '—';
    if (m.cv_r2_mean !== undefined && m.cv_r2_mean !== null && !isNaN(m.cv_r2_mean)) {
      const stdStr = (m.cv_r2_std !== undefined && m.cv_r2_std !== null && !isNaN(m.cv_r2_std))
        ? ` ± ${m.cv_r2_std.toFixed(3)}`
        : '';
      cvStr = `${m.cv_r2_mean.toFixed(3)}${stdStr}`;
    }

    const rmseVal = m.rmse !== undefined && m.rmse !== null && !isNaN(m.rmse) ? m.rmse.toFixed(4) : undefined;

    return {
      taskType: 'regression',
      label: 'Test R²',
      shortLabel: 'R²',
      value: isValidR2 ? `R² ${plainR2Str}` : '—',
      plainValue: plainR2Str,
      raw: isValidR2 ? rawR2 : null,
      cvValue: cvStr,
      secondaryLabel: 'RMSE',
      secondaryValue: rmseVal,
    };
  } else {
    const rawAcc = m.test_accuracy ?? m.accuracy ?? null;
    const isValidAcc = rawAcc !== null && rawAcc !== undefined && !isNaN(rawAcc) && isFinite(rawAcc);
    const accStr = isValidAcc ? formatAccuracy(rawAcc) : '—';

    let cvStr = '—';
    if (m.cv_accuracy_mean !== undefined && m.cv_accuracy_mean !== null && !isNaN(m.cv_accuracy_mean)) {
      const meanPct = (m.cv_accuracy_mean > 1 ? m.cv_accuracy_mean : m.cv_accuracy_mean * 100).toFixed(1);
      const stdPct = (m.cv_accuracy_std !== undefined && m.cv_accuracy_std !== null && !isNaN(m.cv_accuracy_std))
        ? (m.cv_accuracy_std > 1 ? m.cv_accuracy_std : m.cv_accuracy_std * 100).toFixed(1)
        : '0.0';
      cvStr = `${meanPct}% ± ${stdPct}%`;
    }

    let f1Str: string | undefined = undefined;
    if (m.f1_score !== undefined && m.f1_score !== null && !isNaN(m.f1_score)) {
      const f1Val = m.f1_score > 1 ? m.f1_score / 100.0 : m.f1_score;
      f1Str = f1Val.toFixed(3);
    }

    return {
      taskType: 'classification',
      label: 'Test Accuracy',
      shortLabel: 'Accuracy',
      value: accStr,
      plainValue: accStr,
      raw: isValidAcc ? rawAcc : null,
      cvValue: cvStr,
      secondaryLabel: 'F1 Score',
      secondaryValue: f1Str,
    };
  }
}

/**
 * Filter and map experiment list into chart-ready data points, validating all values.
 * Rejects invalid, undefined, NaN, or Infinity scores.
 */
export function prepareChartData(experiments: any[], targetTaskType?: TaskType): ChartMetricPoint[] {
  const completed = experiments.filter(e => e.status === 'completed');
  const points: ChartMetricPoint[] = [];

  for (const exp of completed) {
    const taskType = detectTaskType(exp);
    if (targetTaskType && taskType !== targetTaskType) {
      continue;
    }

    const formatted = formatExperimentMetric(exp);
    if (formatted.raw === null || formatted.raw === undefined || isNaN(formatted.raw) || !isFinite(formatted.raw)) {
      continue;
    }

    let chartScore = formatted.raw;
    if (taskType === 'classification') {
      // Classification percentage scale for Recharts (0 to 100)
      chartScore = formatted.raw > 1.0 ? formatted.raw : formatted.raw * 100.0;
    }

    points.push({
      name: exp.algorithm || 'Model',
      algorithm: exp.algorithm || 'Model',
      score: chartScore,
      displayValue: formatted.plainValue,
      size: exp.model_size_bytes ?? 0,
      taskType,
      rawScore: formatted.raw,
    });
  }

  return points;
}
