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

export interface Report {
  strengths: CompetencyEntry[];
  weaknesses: CompetencyEntry[];
  radar: RadarDomain[];
  priorities: string[];
  competencies_assessed: number;
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
