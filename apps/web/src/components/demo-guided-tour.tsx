"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  Compass,
  ArrowRight,
  ArrowLeft,
  X,
  ShieldCheck,
  Cpu,
  Split,
  Calculator,
  BriefcaseBusiness,
  ShieldAlert,
  BarChart3,
  Minimize2,
  Maximize2,
} from "lucide-react";

export type TourStep = {
  id: string;
  badge: string;
  title: string;
  route: string;
  description: string;
  highlightText?: string;
  icon: typeof Compass;
};

export const TOUR_STEPS: TourStep[] = [
  {
    id: "sandbox",
    badge: "Architectural Isolation",
    title: "1. The Public Demo Sandbox",
    route: "/demo",
    description:
      "AlphaDesk features strict architectural isolation. This Green Demo Workspace is 100% anonymous, execution-incapable, and cannot construct a broker adapter. It allows judges to evaluate the platform instantly without credentials or market hours.",
    highlightText: "Notice the 'DEMO · SYNTHETIC DATA' and 'EXECUTION: DISABLED' badges.",
    icon: ShieldCheck,
  },
  {
    id: "pipeline",
    badge: "Deterministic Core",
    title: "2. The 5-Stage Decision Pipeline",
    route: "/demo",
    description:
      "Every candidate progresses through 5 deterministic stages: Quant Signal → Trade Idea → Candidate Structure → Risk Decision → Order Intent. Unlike unconstrained LLM trading bots, an AI never touches broker state or order construction.",
    highlightText: "Look at the 'Completed deterministic chain' pipeline above.",
    icon: Cpu,
  },
  {
    id: "replays",
    badge: "Scenario Variety",
    title: "3. TRADE, NO TRADE & VETOED",
    route: "/demo/opportunities",
    description:
      "A disciplined desk knows when NOT to trade. The backend provides deterministic replays for approved trades, disciplined NO_TRADE decisions (insufficient confirmation), and RISK_REJECTED vetoes (portfolio caps breached).",
    highlightText: "Try clicking between 'TRADE', 'NO TRADE', and 'VETOED' on this page to observe the live rationale.",
    icon: Split,
  },
  {
    id: "options-math",
    badge: "Defined-Risk Math",
    title: "4. Mathematical Safety Bounds",
    route: "/demo/opportunities",
    description:
      "AlphaDesk supports 8 defined-risk options structures (e.g. Bull Call Spreads). Worst-case maximum loss is mathematically bounded before submission, Greeks are strictly aggregated, and undefined-risk short options are rejected by construction.",
    highlightText: "Observe the Maximum Loss and Maximum Profit metrics strictly bounded on the selected candidate card.",
    icon: Calculator,
  },
  {
    id: "positions",
    badge: "Portfolio & State Projections",
    title: "5. Positions & Working Orders",
    route: "/demo/positions",
    description:
      "AlphaDesk maintains internal CQRS read models for account equity, multi-leg spread positions, and order states. In connected mode, state is reconciled against Alpaca trade updates with broker truth prevailing on any discrepancy.",
    highlightText: "Review the active NVDA Bull Call Spread position, current market marks, and reconciled working orders.",
    icon: BriefcaseBusiness,
  },
  {
    id: "guardian",
    badge: "Supervisory Health",
    title: "6. Guardian Risk Supervisor",
    route: "/demo/audit",
    description:
      "The Guardian engine continuously monitors 8 trigger conditions including broker divergence, stale market data, and order frequency. You can test the emergency manual kill switch and observe reconciliation-gated recovery.",
    highlightText: "Click 'Activate demo kill switch' below to simulate a fail-closed supervisory halt, then click 'Reset demo session'.",
    icon: ShieldAlert,
  },
  {
    id: "lab",
    badge: "Alpha Verification",
    title: "7. Strategy Lab & Point-in-Time Proof",
    route: "/demo/strategy-lab",
    description:
      "Paper profits are not proof of alpha. The Strategy Lab enforces a point-in-time firewall (SimulationClock), data fingerprinting (SHA-256), slippage/fee cost models, and walk-forward validation before promotion.",
    highlightText: "Notice the bitemporal firewall and cost-adjusted metrics that prove viability beyond in-sample curves.",
    icon: BarChart3,
  },
];

const STORAGE_KEY_OPEN = "alphadesk_demo_tour_open";
const STORAGE_KEY_STEP = "alphadesk_demo_tour_step";
const STORAGE_KEY_MINIMIZED = "alphadesk_demo_tour_minimized";

export function DemoGuidedTour() {
  const router = useRouter();
  const pathname = usePathname();

  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  // Initialize from sessionStorage on mount
  useEffect(() => {
    try {
      const savedOpen = sessionStorage.getItem(STORAGE_KEY_OPEN);
      const savedStep = sessionStorage.getItem(STORAGE_KEY_STEP);
      const savedMinimized = sessionStorage.getItem(STORAGE_KEY_MINIMIZED);

      if (savedOpen === "true") {
        const timer = setTimeout(() => {
          setIsOpen(true);
          if (savedStep !== null) {
            const parsedStep = parseInt(savedStep, 10);
            if (!isNaN(parsedStep) && parsedStep >= 0 && parsedStep < TOUR_STEPS.length) {
              setCurrentStepIndex(parsedStep);
            }
          }
          if (savedMinimized === "true") {
            setIsMinimized(true);
          }
        }, 0);
        return () => clearTimeout(timer);
      }
    } catch {
      // sessionStorage unavailable
    }
  }, []);

  function saveState(open: boolean, stepIdx: number, minimized: boolean) {
    try {
      sessionStorage.setItem(STORAGE_KEY_OPEN, open ? "true" : "false");
      sessionStorage.setItem(STORAGE_KEY_STEP, stepIdx.toString());
      sessionStorage.setItem(STORAGE_KEY_MINIMIZED, minimized ? "true" : "false");
    } catch {
      // ignore
    }
  }

  function goToStep(index: number) {
    if (index < 0 || index >= TOUR_STEPS.length) return;
    const targetStep = TOUR_STEPS[index];
    setCurrentStepIndex(index);
    saveState(true, index, false);
    setIsMinimized(false);

    if (pathname !== targetStep.route) {
      router.push(targetStep.route);
    }
  }

  function next() {
    if (currentStepIndex < TOUR_STEPS.length - 1) {
      goToStep(currentStepIndex + 1);
    } else {
      closeTour();
    }
  }

  function prev() {
    if (currentStepIndex > 0) {
      goToStep(currentStepIndex - 1);
    }
  }

  function startTour() {
    goToStep(0);
    setIsOpen(true);
    setIsMinimized(false);
  }

  function closeTour() {
    setIsOpen(false);
    setIsMinimized(false);
    saveState(false, 0, false);
  }

  function toggleMinimize() {
    const nextVal = !isMinimized;
    setIsMinimized(nextVal);
    saveState(isOpen, currentStepIndex, nextVal);
  }

  const step = TOUR_STEPS[currentStepIndex];
  const StepIcon = step?.icon ?? Compass;
  const isFirst = currentStepIndex === 0;
  const isLast = currentStepIndex === TOUR_STEPS.length - 1;

  return (
    <>
      {/* On-page banner trigger when on /demo */}
      {pathname === "/demo" && !isOpen && (
        <div className="tour-trigger-strip">
          <div className="tour-trigger-content">
            <Compass className="tour-trigger-icon" />
            <div>
              <strong>Judge & Evaluator Interactive Walkthrough</strong>
              <p>Step-by-step tour explaining the decision lifecycle, options math, and risk controls across all screens.</p>
            </div>
          </div>
          <button
            type="button"
            onClick={startTour}
            className="tour-start-button"
          >
            <Compass style={{ width: 15, height: 15 }} />
            Start Interactive Tour
          </button>
        </div>
      )}

      {/* Floating launcher when tour is minimized or closed but on demo pages */}
      {!isOpen && pathname !== "/demo" && (
        <button
          type="button"
          className="tour-floating-launcher"
          onClick={startTour}
          aria-label="Start Guided Tour"
        >
          <Compass style={{ width: 16, height: 16 }} />
          <span>Interactive Tour</span>
        </button>
      )}

      {/* Minimized badge */}
      {isOpen && isMinimized && (
        <div className="tour-minimized-pill" onClick={toggleMinimize}>
          <Compass style={{ width: 16, height: 16 }} />
          <span>Tour Step {currentStepIndex + 1}/{TOUR_STEPS.length}: {step.title}</span>
          <Maximize2 style={{ width: 14, height: 14 }} />
        </div>
      )}

      {/* Full Tour Card */}
      {isOpen && !isMinimized && (
        <div className="tour-card" role="dialog" aria-modal="true" aria-label="Demo Guided Tour">
          <div className="tour-header">
            <div className="tour-step-badge">
              <span>{step.badge}</span>
              <small>Step {currentStepIndex + 1} of {TOUR_STEPS.length}</small>
            </div>
            <div className="tour-header-actions">
              <button
                type="button"
                className="tour-icon-btn"
                onClick={toggleMinimize}
                title="Minimize Tour"
                aria-label="Minimize Tour"
              >
                <Minimize2 style={{ width: 14, height: 14 }} />
              </button>
              <button
                type="button"
                className="tour-close-button"
                onClick={closeTour}
                title="Close Tour"
                aria-label="Close Tour"
              >
                <X style={{ width: 15, height: 15 }} />
              </button>
            </div>
          </div>

          <div className="tour-body">
            <div className="tour-title-row">
              <div className="tour-icon-box">
                <StepIcon style={{ width: 18, height: 18 }} />
              </div>
              <h4>{step.title}</h4>
            </div>
            <p className="tour-description">{step.description}</p>
            {step.highlightText && (
              <div className="tour-highlight-box">
                <strong>Focus:</strong> {step.highlightText}
              </div>
            )}
          </div>

          <div className="tour-footer">
            <div className="tour-dots">
              {TOUR_STEPS.map((s, idx) => (
                <button
                  key={s.id}
                  type="button"
                  className={`tour-dot ${idx === currentStepIndex ? "active" : ""}`}
                  onClick={() => goToStep(idx)}
                  title={`Go to step ${idx + 1}: ${s.title}`}
                  aria-label={`Go to step ${idx + 1}`}
                />
              ))}
            </div>

            <div className="tour-buttons">
              {!isFirst && (
                <button
                  type="button"
                  onClick={prev}
                  className="tour-nav-button secondary"
                >
                  <ArrowLeft style={{ width: 13, height: 13 }} />
                  Back
                </button>
              )}
              <button
                type="button"
                onClick={next}
                className="tour-nav-button primary"
              >
                {isLast ? "Finish Tour" : "Next"}
                {!isLast && <ArrowRight style={{ width: 13, height: 13 }} />}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
