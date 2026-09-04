export type BrokerState =
  | "NOT_CONFIGURED"
  | "UNKNOWN"
  | "RECONCILING"
  | "RECONCILED"
  | "DIVERGENT";

export interface SystemStatus {
  mode: "PAPER_ONLY";
  environment: string;
  broker_state: BrokerState;
  autonomous_execution_enabled: boolean;
  guardian_halted: boolean;
  guardian_reason: string | null;
}

export const h0SystemStatus: SystemStatus = {
  mode: "PAPER_ONLY",
  environment: "development",
  broker_state: "NOT_CONFIGURED",
  autonomous_execution_enabled: false,
  guardian_halted: true,
  guardian_reason: "H1 broker reconciliation has not been configured.",
};

