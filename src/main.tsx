import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowDownToLine,
  ArrowRight,
  Check,
  ChevronRight,
  CircleHelp,
  Code2,
  DoorOpen,
  FlaskConical,
  Inbox,
  ListChecks,
  LoaderCircle,
  Mail,
  MessageCircle,
  Pause,
  PencilLine,
  Play,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  X,
} from "lucide-react";
import type {
  EvalCase,
  Evaluation,
  Label,
  Message,
  Row,
  State,
  Suite,
} from "./types";
import "./styles.css";
import "./identity.css";

type Page = "desk" | "review" | "lab" | "evaluation";
const labels: Record<Label, string> = {
  legitimate: "Legitimate",
  spam: "Spam",
  phishing: "Phishing",
};
const percent = (v: number) => `${(v * 100).toFixed(1)}%`;
const waitLabel: Record<string, string> = {
  pending: "Waiting",
  screening: "Screening",
  error: "Call failed",
};
async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(
    `/api${path}`,
    body === undefined
      ? undefined
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Request failed (${response.status})`,
    );
  }
  return response.json() as Promise<T>;
}
function Badge({ label }: { label: Label | string }) {
  return (
    <span className={`badge ${label}`}>{labels[label as Label] || label}</span>
  );
}
function ModelMark() {
  return (
    <span className="model-mark">
      <span />
      <span />
      <span />
      <span />
    </span>
  );
}
function Channel({ channel }: { channel: string }) {
  return channel === "community" ? (
    <MessageCircle size={15} />
  ) : channel === "contact form" ? (
    <Code2 size={15} />
  ) : (
    <Mail size={15} />
  );
}

function App() {
  const [page, setPage] = useState<Page>("desk");
  const [state, setState] = useState<State | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [selected, setSelected] = useState("D02");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [mode, setMode] = useState<"recorded" | "live">("recorded");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<Row | null>(null);
  const [notice, setNotice] = useState("");
  const [showAbout, setShowAbout] = useState(false);
  const refresh = async () => setState(await api<State>("/state"));
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const data = await api<State>("/state");
        if (active) setState(data);
      } catch (e) {
        if (active) setError((e as Error).message);
      }
      if (active) timer = setTimeout(poll, 900);
    };
    void poll();
    void api<Evaluation>("/evaluation")
      .then((d) => {
        if (active) setEvaluation(d);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, []);
  const rows = state?.messages || [];
  const screened = rows.filter((r) => r.status === "screened");
  const review = screened.filter(
    (r) => r.prediction?.route === "review" && !r.review,
  );
  const inbox = screened.filter((r) => r.prediction?.route === "inbox");
  const pending = rows.filter((r) => ["pending", "error"].includes(r.status));
  const visible = rows.filter(
    (r) =>
      (page !== "review" || (r.prediction?.route === "review" && !r.review)) &&
      (filter === "all" || r.message.channel === filter) &&
      `${r.message.subject} ${r.message.body} ${r.message.sender}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const selectedVisible = visible.find((r) => r.id === selected) || visible[0];
  async function act(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const nav: [Page, string, React.ReactNode][] = [
    ["desk", "Screening desk", <Inbox size={18} />],
    ["review", "Review queue", <ListChecks size={18} />],
    ["lab", "Model lab", <FlaskConical size={18} />],
    ["evaluation", "Evaluation", <SlidersHorizontal size={18} />],
  ];
  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <header className="post-header">
        <a className="post-brand" href="#desk" onClick={() => setPage("desk")}>
          frontdoor<span>THE CORRESPONDENCE ROOM</span>
        </a>
        <div className="post-intro">
          A place for messages.
          <br />A second opinion on what they mean.
        </div>
        <svg className="postmark" viewBox="0 0 220 100" aria-hidden="true">
          <circle cx="54" cy="50" r="42" />
          <circle cx="54" cy="50" r="35" />
          <text x="54" y="43" textAnchor="middle">
            LOCAL
          </text>
          <text x="54" y="62" textAnchor="middle">
            LAYA
          </text>
          <path d="M101 28q15-10 30 0t30 0t30 0t30 0M101 43q15-10 30 0t30 0t30 0t30 0M101 58q15-10 30 0t30 0t30 0t30 0M101 73q15-10 30 0t30 0t30 0t30 0" />
        </svg>
      </header>
      <div className="post-navigation">
        <nav aria-label="Main navigation">
          {nav.map(([key, label], index) => (
            <button
              key={key}
              className={`nav-item ${page === key ? "active" : ""}`}
              onClick={() => {
                setPage(key);
                setFilter("all");
                setQuery("");
              }}
              aria-current={page === key ? "page" : undefined}
            >
              <span className="post-tab-number" aria-hidden="true">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span>{label}</span>
              {key === "review" && (
                <span className="nav-count">{review.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="post-links">
          <a
            href="https://github.com/debojitroy/frontdoor"
            target="_blank"
            rel="noreferrer"
          >
            <Code2 size={15} /> Open source <ArrowRight size={14} />
          </a>
          <button onClick={() => setShowAbout(true)}>
            <CircleHelp size={15} /> About this experiment
          </button>
        </div>
      </div>
      <main id="main">
        <header className="topbar">
          <span>
            FRONTDOOR /{" "}
            <strong>{nav.find((n) => n[0] === page)?.[1].toUpperCase()}</strong>
          </span>
          <span
            className={`connection ${state?.config.live_enabled ? "enabled" : ""}`}
          >
            <i />
            {state?.config.live_enabled
              ? "Live model configured"
              : "Recorded demo available"}
          </span>
        </header>
        {error && (
          <div className="alert" role="alert">
            {error}
            <button aria-label="Dismiss error" onClick={() => setError("")}>
              <X size={16} />
            </button>
          </div>
        )}
        <div className="sr-only" role="status">
          {notice ||
            (state?.job.running
              ? `Screened ${state.job.completed} of ${state.job.total} messages`
              : "")}
        </div>
        {(page === "desk" || page === "review") && (
          <>
            <section className="page-heading">
              <div>
                <span className="eyebrow">
                  {page === "desk"
                    ? "01 / INCOMING CORRESPONDENCE"
                    : "02 / HUMAN REVIEW"}
                </span>
                <h1>
                  {page === "desk"
                    ? "The sorting desk."
                    : "Needs another look."}
                </h1>
                <p>
                  {page === "desk"
                    ? "Open a message. Read the model’s decision. Make your own call."
                    : "Inspect the decision. Add your correction. Keep the original evidence."}
                </p>
              </div>
              <div className="heading-action">
                {page === "review" ? (
                  <a className="button secondary" href="/api/export/reviews">
                    <ArrowDownToLine size={16} /> Export reviews
                  </a>
                ) : (
                  <button
                    className="button primary"
                    disabled={busy || state?.job.running || !pending.length}
                    onClick={() => void act(() => api("/run", { mode }))}
                  >
                    {state?.job.running ? (
                      <LoaderCircle className="spin" size={17} />
                    ) : (
                      <Play size={16} fill="currentColor" />
                    )}
                    {state?.job.running
                      ? `Screening ${state.job.completed}/${state.job.total}`
                      : !pending.length && state
                        ? "Stream complete"
                        : "Run demo stream"}
                  </button>
                )}
              </div>
            </section>
            <section className="desk-stats" aria-label="Screening totals">
              <div>
                <span>Incoming messages</span>
                <strong>
                  {rows.length.toString().padStart(2, "0")}
                  <small>across 3 channels</small>
                </strong>
              </div>
              <div>
                <span>Screened by Laya</span>
                <strong>
                  {screened.length.toString().padStart(2, "0")}
                  <small>inspect every decision</small>
                </strong>
              </div>
              <div>
                <span>
                  <i className="dot amber" /> Awaiting review
                </span>
                <strong>
                  {review.length.toString().padStart(2, "0")}
                  <small>human judgment welcome</small>
                </strong>
              </div>
              <div>
                <span>
                  <i className="dot green" /> Inbox suggestions
                </span>
                <strong>
                  {inbox.length.toString().padStart(2, "0")}
                  <small>simulated routing only</small>
                </strong>
              </div>
            </section>
            <div className="desk-toolbar">
              <div className="mode-switch" aria-label="Inference mode">
                <button
                  aria-pressed={mode === "recorded"}
                  className={mode === "recorded" ? "chosen" : ""}
                  onClick={() => setMode("recorded")}
                >
                  Recorded run
                </button>
                <button
                  aria-pressed={mode === "live"}
                  disabled={!state?.config.live_enabled}
                  className={mode === "live" ? "chosen" : ""}
                  onClick={() => setMode("live")}
                >
                  Live inference
                </button>
              </div>
              <p>
                {mode === "recorded"
                  ? "Real saved outputs. The stream is paced for playback."
                  : "Fresh predictions from your configured local Laya worker."}
              </p>
              <span className="mono">NO MESSAGES SENT</span>
            </div>
            <section className="desk">
              <div className="message-list">
                <div className="list-tools">
                  <label className="search">
                    <Search size={16} />
                    <input
                      aria-label="Search messages"
                      placeholder="Search messages…"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                    />
                  </label>
                  <select
                    aria-label="Filter channel"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                  >
                    <option value="all">All channels</option>
                    <option>email</option>
                    <option>contact form</option>
                    <option>community</option>
                  </select>
                </div>
                <div className="list-title">
                  <span>
                    {page === "review"
                      ? "NEEDS YOUR REVIEW"
                      : "INCOMING STREAM"}
                  </span>
                  <span>{visible.length} messages</span>
                </div>
                <div className="message-scroll">
                  {visible.map((r) => (
                    <button
                      key={r.id}
                      onClick={() => setSelected(r.id)}
                      className={`message-row ${selectedVisible?.id === r.id ? "selected" : ""}`}
                      aria-pressed={selectedVisible?.id === r.id}
                    >
                      <div className="message-row-top">
                        <span className="sender">{r.message.sender}</span>
                        <span
                          className="channel-icon"
                          title={r.message.channel}
                        >
                          <Channel channel={r.message.channel} />
                        </span>
                      </div>
                      <strong>{r.message.subject || "(No subject)"}</strong>
                      <p>{r.message.body}</p>
                      <div className="message-row-bottom">
                        <span className="mono">{r.id}</span>
                        {r.review ? (
                          <span className="reviewed">
                            <Check size={12} />
                            Reviewed
                          </span>
                        ) : r.prediction?.verdict ? (
                          <Badge label={r.prediction.verdict} />
                        ) : (
                          <span className={`status-${r.status}`}>
                            {r.status === "screening" && (
                              <LoaderCircle size={12} className="spin" />
                            )}
                            {waitLabel[r.status]}
                          </span>
                        )}
                      </div>
                    </button>
                  ))}
                  {!visible.length && (
                    <div className="empty">
                      <ShieldCheck size={30} />
                      <h3>
                        {page === "review"
                          ? "All clear here."
                          : "No messages found."}
                      </h3>
                      <p>
                        {page === "review"
                          ? "Run the stream to populate the queue, or inspect completed reviews in the screening desk."
                          : "Try a different search or channel."}
                      </p>
                    </div>
                  )}
                </div>
              </div>
              {selectedVisible ? (
                <Inspector
                  key={selectedVisible.id}
                  row={selectedVisible}
                  live={!!state?.config.live_enabled}
                  busy={busy || !!state?.job.running}
                  onEdit={() => setEditing(selectedVisible)}
                  onReview={(label, note) =>
                    void act(async () => {
                      await api(`/messages/${selectedVisible.id}/review`, {
                        label,
                        note,
                      });
                      setNotice(
                        "Review saved. The original model decision is preserved.",
                      );
                    })
                  }
                  bedrock={evaluation?.bedrock?.rows.find(
                    (r) => r.case_id === selectedVisible.id,
                  )}
                />
              ) : (
                <div className="inspector placeholder">
                  <DoorOpen size={54} />
                  <h2>There’s room for good messages.</h2>
                  <p>Select an arrival to inspect its content and decision.</p>
                </div>
              )}
            </section>
            <footer className="desk-footer">
              <span>
                <ShieldCheck size={14} /> Message content stays on this server
                during local inference.
              </span>
              <span>
                Human review is a workflow step, not a confidence guarantee.
              </span>
            </footer>
          </>
        )}
        {page === "lab" &&
          (evaluation ? (
            <ModelLab
              evaluation={evaluation}
              onInspect={() => setPage("evaluation")}
            />
          ) : (
            <Loading />
          ))}
        {page === "evaluation" &&
          (evaluation ? (
            <EvaluationView evaluation={evaluation} />
          ) : (
            <Loading />
          ))}
        {editing && (
          <EditDialog
            row={editing}
            busy={busy}
            close={() => setEditing(null)}
            onSubmit={(message) =>
              void act(async () => {
                const result = await api<Row>("/variants", {
                  message,
                  parent_id: editing.id,
                });
                setSelected(result.id);
                setEditing(null);
                setPage("desk");
                setQuery("");
                setFilter("all");
                if (result.status === "error") throw new Error(result.error);
                setNotice("Fresh prediction saved as a separate message.");
              })
            }
          />
        )}
        {showAbout && (
          <Dialog
            title="An experiment you can inspect."
            close={() => setShowAbout(false)}
          >
            <p>
              FrontDoor is an open-source screening workbench built around Laya,
              a small non-generative decision model. It compares the original
              checkpoint with a supervised specialist and transparent baselines.
            </p>
            <p>
              Recorded mode replays real, exact-input model outputs. Edited
              messages require live inference. Corrections are stored separately
              and exported for offline training.
            </p>
            <p>
              Scores are uncalibrated. The app does not send, delete, or deliver
              email. Sender identity and links are not verified. Published
              evaluations include failures and dataset limitations.
            </p>
            <a
              className="button primary"
              href="https://github.com/debojitroy/frontdoor"
              target="_blank"
              rel="noreferrer"
            >
              Explore the repository <ArrowRight size={16} />
            </a>
          </Dialog>
        )}
      </main>
    </div>
  );
}

function Inspector({
  row,
  live,
  busy,
  onEdit,
  onReview,
  bedrock,
}: {
  row: Row;
  live: boolean;
  busy: boolean;
  onEdit: () => void;
  onReview: (label: Label, note: string) => void;
  bedrock?: { prediction?: Label; error?: string; wall_ms: number };
}) {
  const [label, setLabel] = useState<Label>(
    row.review?.label || row.prediction?.verdict || "legitimate",
  );
  const [note, setNote] = useState(row.review?.note || "");
  const [reviewOpen, setReviewOpen] = useState(false);
  const p = row.prediction;
  return (
    <article className="inspector">
      <div className="inspector-top">
        <span className="eyebrow">MESSAGE / {row.id}</span>
        <div>
          <a
            className="icon-button"
            aria-label="Export decision JSON"
            href={`/api/messages/${row.id}/export`}
          >
            <ArrowDownToLine size={17} />
          </a>
          <button
            className="button quiet"
            disabled={!live || busy}
            onClick={onEdit}
            title={
              !live
                ? "Enable a local worker to test new text"
                : "Create a new message and run fresh inference"
            }
          >
            <PencilLine size={15} /> Edit & test
          </button>
        </div>
      </div>
      <h2>{row.message.subject || "(No subject)"}</h2>
      <div className="from-line">
        <span className="avatar">{row.message.sender.slice(0, 1)}</span>
        <span>
          <strong>{row.message.sender}</strong>
          <small>
            <Channel channel={row.message.channel} /> {row.message.channel}{" "}
            <span>· recipient: your workspace</span>
          </small>
        </span>
      </div>
      <div className="message-body">{row.message.body}</div>
      {row.message.context && (
        <div className="context">
          <span>RECIPIENT CONTEXT</span>
          <p>{row.message.context}</p>
        </div>
      )}
      {p ? (
        <section className="decision">
          <div className="decision-heading">
            <div>
              <ModelMark />
              <span>LAYA DECISION</span>
            </div>
            <Badge label={p.verdict!} />
          </div>
          <div className="scores">
            {(["spam", "phishing"] as const).map((task) => (
              <div className="score" key={task}>
                <div>
                  <span>
                    {task === "spam"
                      ? "Unwanted or unsolicited"
                      : "Deceptive request"}
                  </span>
                  <strong>{percent(p[task]!.positive_probability)}</strong>
                </div>
                <div className="bar-track">
                  <i
                    className={task}
                    style={{ width: `${p[task]!.positive_probability * 100}%` }}
                  />
                </div>
                <small>
                  {task === "spam" ? "Spam score" : "Phishing score"}
                </small>
              </div>
            ))}
          </div>
          <div className="route">
            <span>
              {p.route === "inbox" ? (
                <Inbox size={18} />
              ) : (
                <ListChecks size={18} />
              )}
              <strong>
                {p.route === "inbox" ? "Suggest inbox" : "Send to review"}
              </strong>
              <small>Simulation</small>
            </span>
            <b>
              {row.model_ms?.toFixed(1)}
              <small>ms model time</small>
            </b>
          </div>
          <p className="score-note">
            These are uncalibrated model scores, not a guarantee of safety.
            Recipient context is supplied by the demo; sender identity is not
            authenticated.
          </p>
          <div className="provenance">
            <span className="dot green" />
            <span>
              {row.mode === "recorded"
                ? "Recorded inference"
                : "Fresh inference"}
            </span>
            <span>·</span>
            {row.model?.variant}
            <span>·</span>
            {row.model?.hardware}
          </div>
        </section>
      ) : (
        <section
          className={`waiting ${row.status === "error" ? "failed" : ""}`}
        >
          {row.status === "screening" ? (
            <LoaderCircle className="spin" size={24} />
          ) : (
            <Pause size={24} />
          )}
          <h3>
            {row.status === "error"
              ? "The model call failed."
              : row.status === "screening"
                ? "Laya is taking a look."
                : "Waiting at the front door."}
          </h3>
          <p>
            {row.error ||
              "Run the demo stream to reveal this message’s real model output."}
          </p>
        </section>
      )}
      {p && (
        <>
          <details className="comparison">
            <summary>
              Compare the same message <ChevronRight size={16} />
            </summary>
            <div className="baseline-row">
              <span>
                Keyword rules
                <small>
                  {row.rules?.matched_terms.join(", ") ||
                    "No trigger words matched"}
                </small>
              </span>
              <Badge label={row.rules?.verdict || "unknown"} />
            </div>
            <div className="baseline-row">
              <span>
                TF–IDF + logistic regression
                <small>SMS-trained · binary spam only</small>
              </span>
              <span className="mono">
                {row.tfidf?.spam ? "Spam" : "Not spam"}
              </span>
            </div>
            {bedrock && (
              <div className="baseline-row">
                <span>
                  Bedrock · Sonnet 4.6
                  <small>
                    Recorded API comparison ·{" "}
                    {(bedrock.wall_ms / 1000).toFixed(2)}s
                  </small>
                </span>
                <Badge label={bedrock.prediction || "error"} />
              </div>
            )}
          </details>
          <section className="review-panel">
            {row.review ? (
              <div className="review-saved">
                <Check size={18} />
                <span>
                  <strong>
                    Reviewed as {labels[row.review.label].toLowerCase()}
                  </strong>
                  <small>
                    {row.review.note || "Original model prediction retained."}
                  </small>
                </span>
                <button onClick={() => setReviewOpen(!reviewOpen)}>
                  Edit review
                </button>
              </div>
            ) : (
              <button
                className="review-toggle"
                onClick={() => setReviewOpen(!reviewOpen)}
              >
                <ListChecks size={18} />
                <span>Would you make the same call?</span>
                <ArrowRight size={18} />
              </button>
            )}
            {reviewOpen && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  onReview(label, note);
                  setReviewOpen(false);
                }}
              >
                <label>
                  Your assessment
                  <select
                    value={label}
                    onChange={(e) => setLabel(e.target.value as Label)}
                  >
                    {Object.entries(labels).map(([key, name]) => (
                      <option key={key} value={key}>
                        {name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Review note
                  <textarea
                    maxLength={1000}
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="What should the next model learn from this?"
                  />
                </label>
                <button
                  className="button primary"
                  disabled={busy}
                  type="submit"
                >
                  Save review <Check size={16} />
                </button>
                <p className="muted">
                  Saved separately. It does not rewrite the model output or
                  retrain the model.
                </p>
              </form>
            )}
          </section>
          <details className="audit">
            <summary>
              Decision trail <ChevronRight size={16} />
            </summary>
            {row.events.map((e, i) => (
              <div key={i}>
                <i />
                <span>{e.kind.replaceAll("_", " ")}</span>
                <time>{new Date(e.at).toLocaleTimeString()}</time>
              </div>
            ))}
            <p className="mono">
              Input fingerprint: {row.fingerprint?.slice(0, 20)}…
            </p>
          </details>
        </>
      )}
    </article>
  );
}

function ModelLab({
  evaluation: e,
  onInspect,
}: {
  evaluation: Evaluation;
  onInspect: () => void;
}) {
  const selected = e.history.find(
    (h) => h.epoch === e.training.selected_epoch,
  )!;
  return (
    <div className="lab-page">
      <section className="page-heading">
        <div>
          <span className="eyebrow">FROM BASE MODEL TO SPECIALIST</span>
          <h1>The training notebook.</h1>
          <p>
            A small, supervised experiment. Every example, checkpoint, and
            result accounted for.
          </p>
        </div>
        <a className="button secondary" href="/api/export/reviews">
          <ArrowDownToLine size={16} /> Export your reviews
        </a>
      </section>
      <section className="lab-hero">
        <div>
          <span className="tiny-label">THE EXPERIMENT</span>
          <h2>
            Can examples
            <br />
            sharpen judgment?
          </h2>
          <p>
            We trained Laya’s decision head and final two encoder layers on
            labeled messages. The rest of the model stayed frozen.
          </p>
          <span className="lab-chip">SUPERVISED LEARNING · ONE TESLA T4</span>
        </div>
        <div className="training-flow">
          <div>
            <span>01 / TEACH</span>
            <strong>{e.training.train_examples}</strong>
            <p>training messages</p>
          </div>
          <ArrowRight size={24} />
          <div>
            <span>02 / SELECT</span>
            <strong>{e.training.validation_examples}</strong>
            <p>validation messages</p>
          </div>
          <ArrowRight size={24} />
          <div>
            <span>03 / MEASURE</span>
            <strong>241</strong>
            <p>public test messages</p>
          </div>
        </div>
      </section>
      <div className="lab-columns">
        <section className="panel">
          <div className="panel-title">
            <span className="eyebrow">TRAINING NOTEBOOK</span>
            <span className="mono">
              {e.training.duration_seconds.toFixed(1)}s training
            </span>
          </div>
          <h2>Learning, epoch by epoch.</h2>
          <p>Checkpoint chosen by lowest validation loss. Lower is better.</p>
          <div className="history-chart" aria-label="Validation loss by epoch">
            {e.history.map((h) => (
              <div
                key={h.epoch}
                className={h.epoch === e.training.selected_epoch ? "best" : ""}
              >
                <span>{h.validation_loss.toFixed(3)}</span>
                <i
                  style={{
                    height: `${Math.max(12, (h.validation_loss / Math.max(...e.history.map((v) => v.validation_loss))) * 145)}px`,
                  }}
                />
                <b>{h.epoch}</b>
              </div>
            ))}
          </div>
          <div className="chart-caption">
            <span>
              <i className="dot green" />
              Selected epoch {e.training.selected_epoch}
            </span>
            <span>
              Validation accuracy {percent(selected.validation_accuracy)}
            </span>
          </div>
          <dl className="training-facts">
            <div>
              <dt>Updated parameters</dt>
              <dd>
                {(e.training.trainable_parameters / 1e6).toFixed(1)} million
              </dd>
            </div>
            <div>
              <dt>Checkpoint selection</dt>
              <dd>Validation loss only</dd>
            </div>
            <div>
              <dt>Model scores</dt>
              <dd>Uncalibrated</dd>
            </div>
          </dl>
        </section>
        <section className="panel">
          <span className="eyebrow">THE RESULTS</span>
          <h2>Better has to be measured.</h2>
          <p>
            Published results include regressions. A green training curve alone
            does not establish a useful screening policy.
          </p>
          <table className="result-table">
            <thead>
              <tr>
                <th>Measure</th>
                <th>Base</th>
                <th>Specialist</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>SMS spam recall</td>
                <td>{percent(e.base.summary.sms.laya.recall)}</td>
                <td>{percent(e.specialist.summary.sms.laya.recall)}</td>
              </tr>
              <tr>
                <td>SMS false alarms ↓</td>
                <td>{percent(e.base.summary.sms.laya.false_positive_rate)}</td>
                <td>
                  {percent(e.specialist.summary.sms.laya.false_positive_rate)}
                </td>
              </tr>
              <tr>
                <td>Public phishing recall</td>
                <td>{percent(e.base.summary.phishing.laya.recall)}</td>
                <td>{percent(e.specialist.summary.phishing.laya.recall)}</td>
              </tr>
              <tr>
                <td>Development accuracy</td>
                <td>{percent(e.base.summary.challenge.accuracy)}</td>
                <td>{percent(e.specialist.summary.challenge.accuracy)}</td>
              </tr>
            </tbody>
          </table>
          <div className="quality-note">
            <strong>
              {Object.values(e.specialist.summary.gates).filter(Boolean).length}{" "}
              of {Object.keys(e.specialist.summary.gates).length} frozen quality
              checks pass
            </strong>
            <p>
              Training examples were refined after inspecting base-model
              failures. The 30 authored cases are development evidence, not an
              untouched test set.
            </p>
          </div>
          <button className="button secondary" onClick={onInspect}>
            Inspect the full evaluation <ArrowRight size={16} />
          </button>
        </section>
      </div>
      <section className="learning-strip">
        <div>
          <span className="step-circle">↗</span>
          <div>
            <h3>Your corrections are the next experiment.</h3>
            <p>
              Review a message, export labeled examples, then train and evaluate
              offline. Related variants stay grouped.
            </p>
          </div>
        </div>
        <a href="/api/export/reviews" className="text-link">
          Download reviewed examples <ArrowDownToLine size={16} />
        </a>
      </section>
    </div>
  );
}

function observed(c: EvalCase): Label | string {
  if (c.error || !c.prediction) return "error";
  if (c.dataset === "sms")
    return c.prediction.spam?.choice === "spam" ? "spam" : "not spam";
  if (c.dataset === "phishing")
    return c.prediction.phishing?.choice === "phishing"
      ? "phishing"
      : "not phishing";
  return c.prediction.verdict || "error";
}
function expected(c: EvalCase): string {
  return typeof c.expected === "boolean"
    ? c.expected
      ? c.dataset === "sms"
        ? "spam"
        : "phishing"
      : c.dataset === "sms"
        ? "not spam"
        : "not phishing"
    : c.expected;
}
function BenchmarkTable({
  base,
  specialist,
  spam,
}: {
  base: Suite;
  specialist: Suite;
  spam: boolean;
}) {
  const values = [
    ["Keyword rules", base.rules],
    ...(spam && base.tfidf ? [["TF–IDF + logistic", base.tfidf] as const] : []),
    ["Laya base", base.laya],
    ["Laya specialist", specialist.laya],
  ] as const;
  return (
    <div
      className="table-overflow"
      tabIndex={0}
      role="region"
      aria-label={spam ? "SMS benchmark results" : "Phishing benchmark results"}
    >
      <table className="result-table benchmark">
        <thead>
          <tr>
            <th>Method</th>
            <th>Accuracy</th>
            <th>Recall</th>
            <th>Precision</th>
            <th>False alarms ↓</th>
          </tr>
        </thead>
        <tbody>
          {values.map(([name, v]) => (
            <tr
              key={String(name)}
              className={name === "Laya specialist" ? "highlight" : ""}
            >
              <td>{String(name)}</td>
              <td>{percent(v.accuracy)}</td>
              <td>{percent(v.recall)}</td>
              <td>{percent(v.precision)}</td>
              <td>{percent(v.false_positive_rate)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function EvaluationView({ evaluation: e }: { evaluation: Evaluation }) {
  const [suite, setSuite] = useState("challenge");
  const [wrong, setWrong] = useState(true);
  const [variant, setVariant] = useState<"base" | "specialist">("specialist");
  const cases = e[variant].cases.filter(
    (c) => c.dataset === suite && (!wrong || observed(c) !== expected(c)),
  );
  const gateNames: Record<string, string> = {
    sms_spam_f1: "SMS F1 ≥ 0.90",
    sms_false_positive_rate: "SMS false alarms ≤ 5%",
    challenge_accuracy: "Development accuracy ≥ 85%",
    challenge_phishing_recall: "Development phishing recall ≥ 90%",
    no_execution_errors: "No execution errors",
  };
  return (
    <div className="evaluation-page">
      <section className="page-heading">
        <div>
          <span className="eyebrow">EVIDENCE, INCLUDING THE EXCEPTIONS</span>
          <h1>The evaluation record.</h1>
          <p>
            Fixed examples. Real model outputs. Recomputed scores. No hidden
            failures.
          </p>
        </div>
        <a
          className="button secondary"
          href={`/api/evaluation/${variant}/export`}
        >
          <ArrowDownToLine size={16} /> Raw evaluation
        </a>
      </section>
      <div className="gate-strip">
        {Object.entries(e.specialist.summary.gates).map(([key, pass]) => (
          <span key={key} className={pass ? "pass" : "fail"}>
            {pass ? <Check size={14} /> : <X size={14} />}
            {gateNames[key]}
          </span>
        ))}
      </div>
      <section className="panel eval-suite">
        <div className="suite-header">
          <div>
            <span className="eyebrow">01 / PUBLIC SMS SPAM</span>
            <h2>Catch more. Interrupt less.</h2>
            <p>
              200 SMS messages · 100 spam, 100 legitimate · normalized groups
              kept apart
            </p>
          </div>
          <div className="latency-number">
            {e.specialist.summary.sms.p50_model_ms.toFixed(1)}
            <span>ms median model time · T4</span>
          </div>
        </div>
        <BenchmarkTable
          base={e.base.summary.sms}
          specialist={e.specialist.summary.sms}
          spam
        />
        <p className="dataset-note">
          UCI SMS Spam Collection · CC BY 4.0. Old public data; Laya’s
          pretraining overlap is unknown. This tests SMS spam, not email
          phishing. Balanced sampling does not represent a real inbox’s
          prevalence.
        </p>
      </section>
      <section className="panel eval-suite">
        <div className="suite-header">
          <div>
            <span className="eyebrow">02 / PUBLIC PHISHING</span>
            <h2>A different question. A separate test.</h2>
            <p>
              {e.specialist.summary.phishing.laya.count} messages held out from
              local training · phishing vs benign
            </p>
          </div>
          <div className="latency-number">
            {e.specialist.summary.phishing.laya.tp}
            <span>
              of{" "}
              {e.specialist.summary.phishing.laya.tp +
                e.specialist.summary.phishing.laya.fn}{" "}
              phishing messages detected
            </span>
          </div>
        </div>
        <BenchmarkTable
          base={e.base.summary.phishing}
          specialist={e.specialist.summary.phishing}
          spam={false}
        />
        <p className="dataset-note">
          darkknight25/phishing_benign_email_dataset · dataset card declares
          MIT. Small curated corpus with templated language; labels and
          provenance are not independently audited. This set was inspected after
          the first specialization attempt and is not untouched evidence for
          later experiments.
        </p>
      </section>
      <section className="panel failure-explorer">
        <div className="suite-header">
          <div>
            <span className="eyebrow">03 / CASE EXPLORER</span>
            <h2>The details are the point.</h2>
            <p>
              The 30 authored cases are development examples. Showcase messages
              are reported separately.
            </p>
          </div>
        </div>
        <div className="explorer-tools">
          <label>
            Dataset
            <select
              aria-label="Dataset"
              value={suite}
              onChange={(e) => setSuite(e.target.value)}
            >
              <option value="challenge">Authored development · 30</option>
              <option value="sms">Public SMS · 200</option>
              <option value="phishing">Public phishing · 41</option>
              <option value="showcase">Showcase · 12</option>
            </select>
          </label>
          <label>
            Model
            <select
              aria-label="Model"
              value={variant}
              onChange={(e) =>
                setVariant(e.target.value as "base" | "specialist")
              }
            >
              <option value="specialist">Laya specialist</option>
              <option value="base">Laya base</option>
            </select>
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={wrong}
              onChange={(e) => setWrong(e.target.checked)}
            />{" "}
            Show failures only
          </label>
          <span className="mono">{cases.length} cases</span>
        </div>
        <div className="case-list">
          {cases.map((c) => (
            <details key={c.id}>
              <summary>
                <span className="mono">{c.id}</span>
                <strong>
                  {c.message.subject || c.message.body.slice(0, 75)}
                </strong>
                <span>
                  {observed(c) === expected(c) ? (
                    <Check className="success-icon" size={16} />
                  ) : (
                    <X className="failure-icon" size={16} />
                  )}
                  {observed(c)}
                </span>
                <ChevronRight size={15} />
              </summary>
              <div>
                <p>{c.message.body}</p>
                {c.message.context && (
                  <blockquote>{c.message.context}</blockquote>
                )}
                <div className="case-labels">
                  <span>
                    Expected: <strong>{expected(c)}</strong>
                  </span>
                  <span>
                    Observed: <strong>{observed(c)}</strong>
                  </span>
                  <span>{c.model_ms?.toFixed(1)}ms</span>
                </div>
              </div>
            </details>
          ))}
          {!cases.length && (
            <p className="empty">No cases match this filter.</p>
          )}
        </div>
      </section>
    </div>
  );
}
function Loading() {
  return (
    <div className="empty">
      <LoaderCircle className="spin" size={30} />
      <p>Loading the evidence…</p>
    </div>
  );
}
function Dialog({
  title,
  close,
  children,
}: {
  title: string;
  close: () => void;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault();
        close();
      }}
      aria-labelledby="dialog-title"
    >
      <div className="dialog-top">
        <h2 id="dialog-title">{title}</h2>
        <button
          className="icon-button"
          onClick={close}
          aria-label="Close dialog"
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
function EditDialog({
  row,
  busy,
  close,
  onSubmit,
}: {
  row: Row;
  busy: boolean;
  close: () => void;
  onSubmit: (message: Message) => void;
}) {
  const [message, setMessage] = useState(row.message);
  return (
    <Dialog
      title="Change the message. Test the judgment."
      close={busy ? () => {} : close}
    >
      <p>
        A fresh local prediction is saved as a variant of {row.id}. Your
        original message stays intact.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit(message);
        }}
      >
        <label>
          Subject
          <input
            aria-label="Subject"
            maxLength={160}
            value={message.subject}
            onChange={(e) =>
              setMessage({ ...message, subject: e.target.value })
            }
          />
        </label>
        <label>
          Message body
          <textarea
            aria-label="Message body"
            required
            maxLength={1800}
            rows={6}
            value={message.body}
            onChange={(e) => setMessage({ ...message, body: e.target.value })}
          />
        </label>
        <label>
          Recipient context
          <textarea
            aria-label="Recipient context"
            maxLength={500}
            rows={3}
            value={message.context}
            onChange={(e) =>
              setMessage({ ...message, context: e.target.value })
            }
          />
        </label>
        <div className="dialog-actions">
          <button
            type="button"
            className="button secondary"
            disabled={busy}
            onClick={close}
          >
            Cancel
          </button>
          <button className="button primary" disabled={busy} type="submit">
            {busy ? (
              <LoaderCircle className="spin" size={16} />
            ) : (
              <Play size={16} />
            )}{" "}
            Run fresh inference
          </button>
        </div>
      </form>
    </Dialog>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
