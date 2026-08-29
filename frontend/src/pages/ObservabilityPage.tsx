import { useEffect, useState } from "react";

import * as api from "../api/endpoints";
import type { ObservabilitySummaryResponse } from "../api/types";

import { ChartIcon, ClockIcon, SparkleIcon, WarningIcon } from "../components/icons";
import { useI18n } from "../context/I18nContext";

const DAY_OPTIONS = [7, 30, 90] as const;

export function ObservabilityPage() {
  const { locale } = useI18n();

  const [days, setDays] = useState<(typeof DAY_OPTIONS)[number]>(7);
  const [summary, setSummary] = useState<ObservabilitySummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const copy =
    locale === "tr"
      ? {
          title: "Gözlemlenebilirlik",
          subtitle:
            "Sorularının, agent turlarının ve tool çağrılarının güvenilirlik ve gecikme metrikleri.",
          totalRequests: "Toplam İstek",
          successRate: "Başarı Oranı",
          avgDuration: "Ort. Süre",
          eventsByType: "Olay Türüne Göre",
          dailyActivity: "Günlük Etkinlik",
          topTools: "En Çok Kullanılan Araçlar",
          noTools: "Henüz hiç araç çağrısı yok.",
          noEvents: "Bu aralıkta henüz kayıtlı bir etkinlik yok.",
          retry: "Tekrar dene",
          loadErrorText: "Veriler yüklenemedi. Sunucuya ulaşılamıyor olabilir.",
          days: (n: number) => `${n} gün`,
        }
      : {
          title: "Observability",
          subtitle: "Reliability and latency across your questions, agent turns, and tool calls.",
          totalRequests: "Total Requests",
          successRate: "Success Rate",
          avgDuration: "Avg Duration",
          eventsByType: "Events by Type",
          dailyActivity: "Daily Activity",
          topTools: "Top Tools",
          noTools: "No tool calls recorded yet.",
          noEvents: "No activity recorded in this window yet.",
          retry: "Retry",
          loadErrorText: "Couldn't load your data. The server may be unreachable.",
          days: (n: number) => `${n}d`,
        };

  function loadSummary() {
    setIsLoading(true);
    setLoadError(null);

    api
      .getObservabilitySummary(days)
      .then(setSummary)
      .catch(() => setLoadError(copy.loadErrorText))
      .finally(() => setIsLoading(false));
  }

  useEffect(() => {
    loadSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days]);

  const maxDailyCount = summary
    ? Math.max(1, ...summary.daily_counts.map((d) => d.count))
    : 1;
  const maxToolCount = summary
    ? Math.max(1, ...summary.top_tools.map((t) => t.count))
    : 1;

  return (
    <div className="obs-page">
      <div className="obs-header">
        <div>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>

        <div className="obs-day-toggle" role="tablist">
          {DAY_OPTIONS.map((option) => (
            <button
              key={option}
              type="button"
              role="tab"
              aria-selected={days === option}
              className={days === option ? "active" : ""}
              onClick={() => setDays(option)}
            >
              {copy.days(option)}
            </button>
          ))}
        </div>
      </div>

      {loadError && (
        <div className="obs-error-banner" role="alert">
          <WarningIcon width={16} height={16} />
          <span>{loadError}</span>
          <button type="button" onClick={loadSummary}>
            {copy.retry}
          </button>
        </div>
      )}

      <div className="obs-stat-grid">
        <article className="obs-stat-tile">
          <span className="obs-stat-icon">
            <ChartIcon width={16} height={16} />
          </span>
          <strong>{summary ? summary.total_requests : "—"}</strong>
          <span>{copy.totalRequests}</span>
        </article>

        <article className="obs-stat-tile">
          <span className="obs-stat-icon">
            <SparkleIcon width={16} height={16} />
          </span>
          <strong>
            {summary ? `${Math.round(summary.success_rate * 100)}%` : "—"}
          </strong>
          <span>{copy.successRate}</span>
        </article>

        <article className="obs-stat-tile">
          <span className="obs-stat-icon">
            <ClockIcon width={16} height={16} />
          </span>
          <strong>
            {summary ? `${Math.round(summary.avg_duration_ms)}ms` : "—"}
          </strong>
          <span>{copy.avgDuration}</span>
        </article>
      </div>

      <div className="obs-panels">
        <article className="obs-panel obs-panel-chart">
          <h2>{copy.dailyActivity}</h2>

          {summary && summary.total_requests === 0 ? (
            <p className="obs-empty">{copy.noEvents}</p>
          ) : (
            <div className="obs-bar-chart">
              {(summary?.daily_counts ?? []).map((day) => (
                <div className="obs-bar-column" key={day.date}>
                  <div
                    className="obs-bar"
                    style={{
                      height: `${Math.max(4, (day.count / maxDailyCount) * 100)}%`,
                    }}
                    title={`${day.date}: ${day.count}`}
                  />
                  <span>{day.date.slice(5)}</span>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="obs-panel">
          <h2>{copy.eventsByType}</h2>

          {summary && Object.keys(summary.events_by_type).length === 0 ? (
            <p className="obs-empty">{copy.noEvents}</p>
          ) : (
            <ul className="obs-type-list">
              {Object.entries(summary?.events_by_type ?? {}).map(
                ([type, count]) => (
                  <li key={type}>
                    <span>{type}</span>
                    <strong>{count}</strong>
                  </li>
                ),
              )}
            </ul>
          )}
        </article>

        <article className="obs-panel">
          <h2>{copy.topTools}</h2>

          {summary && summary.top_tools.length === 0 ? (
            <p className="obs-empty">{copy.noTools}</p>
          ) : (
            <ul className="obs-tool-list">
              {(summary?.top_tools ?? []).map((tool) => (
                <li key={tool.tool_name}>
                  <div className="obs-tool-list-label">
                    <span>{tool.tool_name}</span>
                    <strong>{tool.count}</strong>
                  </div>
                  <div className="obs-tool-list-track">
                    <div
                      className="obs-tool-list-fill"
                      style={{ width: `${(tool.count / maxToolCount) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </article>
      </div>

      {isLoading && !summary && <p className="obs-loading">…</p>}
    </div>
  );
}
