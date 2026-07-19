// Mirrors the backend payloads (app/models.py + report node output).

export type Role = "assistant" | "user" | "tool" | "grade";

export interface ToolResult {
  title: string;
  url: string;
  source: string;
}

export interface GradeCheck {
  id: string;
  description: string;
  passed: boolean;
}

export interface Grade {
  competency_id: string;
  level: number;
  deterministic_score: number;
  checks: GradeCheck[];
  evidence: string;
}

export interface ChatMessage {
  role: Role;
  content: string;
  streaming?: boolean;
  tool?: { name: string; result: ToolResult };
  grade?: Grade;
}

export interface CompetencyEntry {
  competency_id: string;
  competency_name: string;
  domain_id: string;
  current_level: number;
  target_level: number;
  gap: number;
  priority: number;
  evidence: string;
}

export interface RadarDomain {
  domain_id: string;
  domain_name: string;
  weight: string;
  current: number;
  target: number;
}

export interface RoadmapMilestone {
  rank: number;
  competency_id: string;
  competency_name: string;
  domain_name: string;
  domain_weight: string;
  from_level: number;
  from_level_name: string;
  target_level: number;
  target_level_name: string;
  focus: string;
  why: string;
  practice: string[];
  signal: string;
  has_exercise?: boolean; // a graded code challenge exists for this competency
  resources?: ResourceLink[];
}

export interface ResourceLink {
  title: string;
  url: string;
}

export interface BenchmarkDomain {
  domain_id: string;
  domain_name: string;
  you: number;
  typical: number;
  percentile: number;
  standing: string; // "ahead of most" | "about typical" | "behind most"
}

export interface RolePreset {
  key: string;
  label: string;
  description: string;
}

export interface DueItem {
  competency_id: string;
  competency_name: string;
  current_level: number;
  target_level: number;
  days_overdue: number;
  still_weak: boolean;
}

export interface Exercise {
  competency_id: string;
  title: string;
  language: string;
  prompt: string;
}

export interface GradeCheck {
  id: string;
  description: string;
  passed: boolean;
}

export interface GradeResult {
  competency_id: string;
  level: number;
  target_level: number;
  confidence: number;
  deterministic_score: number;
  evidence: string;
  checks: GradeCheck[];
  execution?: { ran: boolean; passed: boolean; error?: string } | null;
}

export interface Roadmap {
  horizon: string;
  milestones: RoadmapMilestone[];
}

export interface Report {
  strengths: CompetencyEntry[];
  weaknesses: CompetencyEntry[];
  radar: RadarDomain[];
  priorities: string[];
  competencies_assessed: number;
  role_title?: string; // set when targets came from a pasted JD
  verdict?: string; // hiring read, set in interview mode
  interview?: boolean; // true when produced by a mock-interview session
  roadmap?: Roadmap; // personalized growth plan (coaching mode)
  benchmark?: BenchmarkDomain[]; // where you stand vs a typical engineer
  source?: string; // "code" when diagnosed from real artifacts
}

export interface LedgerEntry {
  competency_id: string;
  baseline_level: number | null;
  current_level: number | null;
  target_level: number | null;
  growth: number | null;
}

export interface Profile {
  goal: string;
  background: string;
  target_role: string;
  jd?: string; // optional pasted job description → role-specific targets
  role?: string; // optional role-preset key → target overlay
}

// WebSocket server → client events.
export interface ServerEvent {
  type:
    | "assistant_message"
    | "message_start"
    | "token"
    | "message_end"
    | "tool_call"
    | "exercise"
    | "grade"
    | "report"
    | "phase"
    | "notice"
    | "done"
    | "error";
  thread_id?: string;
  content?: string;
  text?: string;
  name?: string;
  result?: ToolResult;
  phase?: string;
  data?: any;
  // grade event
  competency_id?: string;
  level?: number;
  deterministic_score?: number;
  checks?: GradeCheck[];
  evidence?: string;
}

export type SessionStatus =
  | "idle"
  | "connecting"
  | "thinking"
  | "awaiting_input"
  | "done"
  | "error";
