export type Label = "legitimate" | "spam" | "phishing";
export type Message = {
  channel: "email" | "contact form" | "community";
  sender: string;
  subject: string;
  body: string;
  context: string;
};
export type Decision = {
  choice: string;
  positive_probability: number;
  probabilities: Record<string, number>;
};
export type Prediction = {
  spam?: Decision;
  phishing?: Decision;
  verdict?: Label;
  route?: "inbox" | "review";
};
export type Metadata = {
  model_repo: string;
  model_revision: string;
  variant: string;
  hardware: string;
  adapter_sha256: string | null;
};
export type Row = {
  id: string;
  parent_id: string | null;
  message: Message;
  status: "pending" | "screening" | "screened" | "error";
  prediction: Prediction | null;
  review: { label: Label; note: string; at: string } | null;
  events: { kind: string; at: string }[];
  error?: string;
  mode?: string;
  model_ms?: number;
  model?: Metadata;
  fingerprint?: string;
  rules?: { verdict: Label; matched_terms: string[] };
  tfidf?: { spam: boolean; probability: number; scope: string };
};
export type State = {
  messages: Row[];
  job: { running: boolean; completed: number; total: number; mode: string };
  config: { live_enabled: boolean; recorded_model: Metadata };
};
export type Binary = {
  count: number;
  correct: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  false_positive_rate: number;
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  errors: number;
};
export type Suite = {
  laya: Binary;
  rules: Binary;
  tfidf?: Binary;
  p50_model_ms: number;
  p95_model_ms: number;
};
export type Summary = {
  sms: Suite;
  phishing: Suite;
  challenge: {
    count: number;
    correct: number;
    accuracy: number;
    phishing_recall: number;
    legitimate_false_flags: number;
    p50_model_ms: number;
  };
  showcase: {
    count: number;
    correct: number;
    accuracy: number;
    p50_model_ms: number;
  };
  gates: Record<string, boolean>;
};
export type EvalCase = {
  id: string;
  dataset: string;
  expected: boolean | Label;
  prediction?: Prediction;
  error?: string;
  model_ms: number;
  message: Pick<Message, "body" | "subject" | "context">;
};
export type Report = {
  summary: Summary;
  metadata: Metadata;
  created_at: string;
  cases: EvalCase[];
};
export type Evaluation = {
  base: Report;
  specialist: Report;
  training: {
    train_examples: number;
    validation_examples: number;
    trainable_parameters: number;
    duration_seconds: number;
    selected_epoch: number;
    epochs: number;
    adapter_sha256: string;
    public_phishing: { test: number };
  };
  history: {
    epoch: number;
    train_loss: number;
    validation_loss: number;
    validation_accuracy: number;
    skipped_steps?: number;
  }[];
  bedrock: {
    metadata: { model_id: string };
    rows: {
      case_id: string;
      dataset: string;
      prediction?: Label;
      expected: Label;
      error?: string;
      wall_ms: number;
    }[];
  } | null;
};
