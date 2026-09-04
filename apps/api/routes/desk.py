from __future__ import annotations

# FastAPI dependencies are intentionally declared in parameter defaults.
# ruff: noqa: B008
import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import delete, select

from packages.ai.provider import OpenRouterProvider
from packages.ai.store import AIWorkflowStore
from packages.ai.workflow import AIWorkflow
from packages.auth.dependencies import WorkspaceContext, require_workspace
from packages.broker.alpaca_adapter import AlpacaPaperBrokerAdapter
from packages.broker.projections import PostgresBrokerProjectionStore
from packages.broker.reconciliation import BrokerExecutionGate
from packages.connected.market_clock import AlpacaMarketClockAdapter, ConnectedMarketClock
from packages.connected.opportunities import (
    ConnectedAnalysis,
    ConnectedOpportunityService,
    complete_scan_run,
    start_scan_run,
)
from packages.database.models import (
    BrokerAccountRecord,
    BrokerOrderRecord,
    BrokerPositionRecord,
    BrokerSyncStateRecord,
    ConnectedOpportunityRecord,
    ConnectedScanRunRecord,
    GuardianIncidentRecord,
    WatchlistSymbolRecord,
    WorkspaceCredentialRecord,
    WorkspaceRecord,
)
from packages.domain.ai import AIWorkflowResult, Citation
from packages.domain.broker import BrokerAccount, BrokerOrder, BrokerPosition, BrokerSyncStatus
from packages.domain.guardian import GuardianStatus, GuardianTrigger
from packages.domain.system import BrokerState
from packages.domain.workflow import OrderIntent, RankedCandidate
from packages.execution.engine import ExecutionBlocked, ExecutionEngine
from packages.execution.store import PostgresIntentStore
from packages.guardian.gate import GuardianExecutionGate
from packages.guardian.store import PostgresGuardianStore
from packages.observability.logging import get_logger
from packages.risk.engine import RiskContext, RiskEngine, RiskPolicy
from packages.security.store import CredentialStore

router = APIRouter(prefix="/desk", tags=["connected-paper"])
logger = get_logger(__name__)


class WorkspaceView(BaseModel):
    model_config = ConfigDict(frozen=True)

    workspace_id: UUID
    mode: Literal["CONNECTED_PAPER"] = "CONNECTED_PAPER"
    status: str
    scanner_enabled: bool
    watchlist_count: int


class CredentialStatusView(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    configured: bool
    enabled: bool
    validation_status: str
    fingerprint: str | None
    configuration: dict[str, Any]
    validated_at: datetime | None
    updated_at: datetime | None


class AlpacaCredentialInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_key_id: SecretStr = Field(min_length=8)
    secret_key: SecretStr = Field(min_length=8)


class OpenRouterCredentialInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_key: SecretStr = Field(min_length=8)
    model: str = Field(min_length=2, max_length=160)


class ProviderTestResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    status: str
    detail: str
    account_status: str | None = None
    model: str | None = None


class ProbeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ok"]
    citation: Citation


class WatchlistInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbols: tuple[str, ...] = Field(max_length=25)


class ScannerInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool


class ScannerFailure(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    code: Literal["REAL_DATA_UNAVAILABLE"] = "REAL_DATA_UNAVAILABLE"


class ScannerResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    scan_run_id: UUID
    trigger: str
    started_at: datetime
    completed_at: datetime
    attempted: int
    results: tuple[ConnectedAnalysis, ...]
    failures: tuple[ScannerFailure, ...]


class ScanRunView(BaseModel):
    model_config = ConfigDict(frozen=True)

    scan_run_id: UUID
    trigger: str
    source: str
    started_at: datetime
    completed_at: datetime | None
    attempted: int
    completed: int
    failed: int


class ConfirmPaperOrder(BaseModel):
    model_config = ConfigDict(frozen=True)

    client_order_id: str = Field(min_length=10, max_length=64)


class ConnectedPreflight:
    def __init__(self, broker: BrokerExecutionGate, guardian: GuardianExecutionGate) -> None:
        self._broker = broker
        self._guardian = guardian

    async def execution_allowed(self) -> tuple[bool, str]:
        guardian_allowed, guardian_reason = await self._guardian.execution_allowed()
        if not guardian_allowed:
            return False, guardian_reason
        broker = await self._broker.evaluate()
        return broker.allowed, broker.reason


def _credential_store(request: Request) -> CredentialStore:
    cipher = request.app.state.credential_cipher
    if cipher is None:
        raise HTTPException(
            status_code=503, detail="Encrypted credential storage is not configured"
        )
    return CredentialStore(request.app.state.database.sessions, cipher)


def _credential_view(
    provider: str, record: WorkspaceCredentialRecord | None
) -> CredentialStatusView:
    if record is None:
        return CredentialStatusView(
            provider=provider,
            configured=False,
            enabled=False,
            validation_status="NOT_CONFIGURED",
            fingerprint=None,
            configuration={},
            validated_at=None,
            updated_at=None,
        )
    return CredentialStatusView(
        provider=provider,
        configured=True,
        enabled=record.enabled,
        validation_status=record.validation_status,
        fingerprint=record.fingerprint,
        configuration=record.configuration,
        validated_at=record.validated_at,
        updated_at=record.updated_at,
    )


@router.get("/workspace", response_model=WorkspaceView)
async def workspace_view(
    request: Request, context: WorkspaceContext = Depends(require_workspace)
) -> WorkspaceView:
    async with request.app.state.database.sessions() as session:
        workspace = await session.get(WorkspaceRecord, context.workspace_id)
        assert workspace is not None
        watchlist_count = len(
            tuple(
                await session.scalars(
                    select(WatchlistSymbolRecord.symbol).where(
                        WatchlistSymbolRecord.workspace_id == context.workspace_id
                    )
                )
            )
        )
    return WorkspaceView(
        workspace_id=context.workspace_id,
        status=workspace.status,
        scanner_enabled=workspace.scanner_enabled,
        watchlist_count=watchlist_count,
    )


@router.get("/credentials", response_model=list[CredentialStatusView])
async def credential_statuses(
    request: Request, context: WorkspaceContext = Depends(require_workspace)
) -> list[CredentialStatusView]:
    async with request.app.state.database.sessions() as session:
        records = {
            record.provider: record
            for record in await session.scalars(
                select(WorkspaceCredentialRecord).where(
                    WorkspaceCredentialRecord.workspace_id == context.workspace_id
                )
            )
        }
    return [
        _credential_view(provider, records.get(provider)) for provider in ("ALPACA", "OPENROUTER")
    ]


async def _test_alpaca(payload: AlpacaCredentialInput) -> ProviderTestResult:
    adapter = AlpacaPaperBrokerAdapter(
        payload.api_key_id.get_secret_value(), payload.secret_key.get_secret_value()
    )
    try:
        snapshot = await asyncio.wait_for(adapter.reconcile(), timeout=20)
        return ProviderTestResult(
            provider="ALPACA",
            status="VERIFIED",
            detail="Paper endpoint authenticated; account, positions, and orders reconciled.",
            account_status=snapshot.account.status,
        )
    except Exception as error:
        raise HTTPException(
            status_code=422,
            detail=f"Alpaca paper validation failed ({type(error).__name__})",
        ) from error
    finally:
        await adapter.close()


@router.post("/credentials/alpaca/test", response_model=ProviderTestResult)
async def test_alpaca_credentials(
    payload: AlpacaCredentialInput,
    _: WorkspaceContext = Depends(require_workspace),
) -> ProviderTestResult:
    return await _test_alpaca(payload)


@router.put("/credentials/alpaca", response_model=CredentialStatusView)
async def save_alpaca_credentials(
    payload: AlpacaCredentialInput,
    request: Request,
    context: WorkspaceContext = Depends(require_workspace),
) -> CredentialStatusView:
    await _test_alpaca(payload)
    record = await _credential_store(request).save(
        workspace_id=context.workspace_id,
        actor_user_id=context.principal.user_id,
        provider="ALPACA",
        secret_payload={
            "api_key_id": payload.api_key_id.get_secret_value(),
            "secret_key": payload.secret_key.get_secret_value(),
        },
        configuration={"endpoint": "PAPER"},
        validation_status="VERIFIED",
        enabled=True,
    )
    async with request.app.state.database.sessions.begin() as session:
        workspace = await session.get(WorkspaceRecord, context.workspace_id)
        assert workspace is not None
        workspace.status = "CONNECTING"
        workspace.updated_at = datetime.now(UTC)
    return _credential_view("ALPACA", record)


async def _test_openrouter(payload: OpenRouterCredentialInput) -> ProviderTestResult:
    provider = OpenRouterProvider(
        payload.api_key.get_secret_value(), model=payload.model, timeout_seconds=20
    )
    try:
        await provider.generate(
            agent_name="AlphaDeskCapabilityProbe",
            instructions="Return status ok and cite the supplied system source. No tools.",
            input_payload='Source: {"source_id":"alphadesk-system","claim":"capability probe"}',
            response_model=ProbeResponse,
        )
    except Exception as error:
        raise HTTPException(
            status_code=422,
            detail=f"OpenRouter model capability probe failed ({type(error).__name__})",
        ) from error
    return ProviderTestResult(
        provider="OPENROUTER",
        status="VERIFIED",
        detail="The model produced a schema-valid read-only response.",
        model=payload.model,
    )


@router.post("/credentials/openrouter/test", response_model=ProviderTestResult)
async def test_openrouter_credentials(
    payload: OpenRouterCredentialInput,
    _: WorkspaceContext = Depends(require_workspace),
) -> ProviderTestResult:
    return await _test_openrouter(payload)


@router.put("/credentials/openrouter", response_model=CredentialStatusView)
async def save_openrouter_credentials(
    payload: OpenRouterCredentialInput,
    request: Request,
    context: WorkspaceContext = Depends(require_workspace),
) -> CredentialStatusView:
    await _test_openrouter(payload)
    record = await _credential_store(request).save(
        workspace_id=context.workspace_id,
        actor_user_id=context.principal.user_id,
        provider="OPENROUTER",
        secret_payload={"api_key": payload.api_key.get_secret_value()},
        configuration={"model": payload.model, "compatibility": "verified"},
        validation_status="VERIFIED",
        enabled=True,
    )
    return _credential_view("OPENROUTER", record)


@router.delete("/credentials/{provider}", status_code=204)
async def delete_credentials(
    provider: Literal["alpaca", "openrouter"],
    request: Request,
    context: WorkspaceContext = Depends(require_workspace),
) -> None:
    normalized = provider.upper()
    await _credential_store(request).delete(
        workspace_id=context.workspace_id,
        actor_user_id=context.principal.user_id,
        provider=normalized,
    )
    if normalized == "ALPACA":
        async with request.app.state.database.sessions.begin() as session:
            for model in (
                BrokerOrderRecord,
                BrokerPositionRecord,
                BrokerAccountRecord,
                BrokerSyncStateRecord,
                GuardianIncidentRecord,
            ):
                await session.execute(
                    delete(model).where(model.workspace_id == context.workspace_id)
                )
            workspace = await session.get(WorkspaceRecord, context.workspace_id)
            assert workspace is not None
            workspace.status = "ONBOARDING"
            workspace.scanner_enabled = False
            workspace.updated_at = datetime.now(UTC)


@router.get("/watchlist", response_model=list[str])
async def get_watchlist(
    request: Request, context: WorkspaceContext = Depends(require_workspace)
) -> list[str]:
    async with request.app.state.database.sessions() as session:
        return list(
            await session.scalars(
                select(WatchlistSymbolRecord.symbol)
                .where(WatchlistSymbolRecord.workspace_id == context.workspace_id)
                .order_by(WatchlistSymbolRecord.symbol)
            )
        )


@router.put("/watchlist", response_model=list[str])
async def replace_watchlist(
    payload: WatchlistInput,
    request: Request,
    context: WorkspaceContext = Depends(require_workspace),
) -> list[str]:
    symbols = tuple(sorted({item.strip().upper() for item in payload.symbols if item.strip()}))
    if len(symbols) > 25 or any(not item.isalnum() or len(item) > 16 for item in symbols):
        raise HTTPException(status_code=422, detail="Watchlist contains invalid symbols")
    now = datetime.now(UTC)
    async with request.app.state.database.sessions.begin() as session:
        await session.execute(
            delete(WatchlistSymbolRecord).where(
                WatchlistSymbolRecord.workspace_id == context.workspace_id
            )
        )
        session.add_all(
            WatchlistSymbolRecord(workspace_id=context.workspace_id, symbol=symbol, created_at=now)
            for symbol in symbols
        )
    return list(symbols)


@router.put("/scanner", response_model=WorkspaceView)
async def set_scanner(
    payload: ScannerInput,
    request: Request,
    context: WorkspaceContext = Depends(require_workspace),
) -> WorkspaceView:
    if payload.enabled:
        credential = await _credential_store(request).get(context.workspace_id, "ALPACA")
        if credential is None or not credential.enabled:
            raise HTTPException(
                status_code=409, detail="Verified Alpaca paper credentials required"
            )
    async with request.app.state.database.sessions.begin() as session:
        workspace = await session.get(WorkspaceRecord, context.workspace_id, with_for_update=True)
        assert workspace is not None
        workspace.scanner_enabled = payload.enabled
        workspace.updated_at = datetime.now(UTC)
        count = len(
            tuple(
                await session.scalars(
                    select(WatchlistSymbolRecord.symbol).where(
                        WatchlistSymbolRecord.workspace_id == context.workspace_id
                    )
                )
            )
        )
        return WorkspaceView(
            workspace_id=workspace.workspace_id,
            status=workspace.status,
            scanner_enabled=workspace.scanner_enabled,
            watchlist_count=count,
        )


async def _opportunity_service(
    request: Request, context: WorkspaceContext
) -> ConnectedOpportunityService:
    secrets = await _credential_store(request).reveal(context.workspace_id, "ALPACA")
    if secrets is None:
        raise HTTPException(status_code=409, detail="Verified Alpaca paper credentials required")
    return ConnectedOpportunityService(
        request.app.state.database.sessions,
        context.workspace_id,
        str(secrets["api_key_id"]),
        str(secrets["secret_key"]),
    )


@router.get("/market-clock", response_model=ConnectedMarketClock)
async def market_clock(
    request: Request,
    context: WorkspaceContext = Depends(require_workspace),
) -> ConnectedMarketClock:
    secrets = await _credential_store(request).reveal(context.workspace_id, "ALPACA")
    if secrets is None:
        raise HTTPException(status_code=409, detail="Verified Alpaca paper credentials required")
    try:
        return await AlpacaMarketClockAdapter(
            str(secrets["api_key_id"]), str(secrets["secret_key"])
        ).get_clock()
    except Exception as error:
        raise HTTPException(
            status_code=422,
            detail=f"Real market clock unavailable ({type(error).__name__})",
        ) from error


@router.post("/opportunities/analyze/{symbol}", response_model=ConnectedAnalysis)
async def analyze_symbol(
    symbol: str,
    request: Request,
    context: WorkspaceContext = Depends(require_workspace),
) -> ConnectedAnalysis:
    try:
        return await (await _opportunity_service(request, context)).analyze(symbol)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=422,
            detail=f"Real-data analysis unavailable ({type(error).__name__})",
        ) from error


@router.post("/scanner/scan", response_model=ScannerResult)
async def scan_now(
    request: Request, context: WorkspaceContext = Depends(require_workspace)
) -> ScannerResult:
    async with request.app.state.database.sessions() as session:
        symbols = list(
            await session.scalars(
                select(WatchlistSymbolRecord.symbol)
                .where(WatchlistSymbolRecord.workspace_id == context.workspace_id)
                .order_by(WatchlistSymbolRecord.symbol)
            )
        )
    service = await _opportunity_service(request, context)
    run = await start_scan_run(
        request.app.state.database.sessions,
        context.workspace_id,
        trigger="MANUAL",
        attempted_count=len(symbols),
    )
    results: list[ConnectedAnalysis] = []
    failures: list[ScannerFailure] = []
    for symbol in symbols:
        try:
            results.append(await service.analyze(symbol, scan_run_id=run.scan_run_id))
        except Exception as error:
            logger.warning(
                "workspace_scan_symbol_unavailable",
                extra={
                    "event": "workspace_scan_symbol_unavailable",
                    "workspace_id": str(context.workspace_id),
                    "symbol": symbol,
                    "failure_type": type(error).__name__,
                },
            )
            failures.append(ScannerFailure(symbol=symbol))
    completed_run = await complete_scan_run(
        request.app.state.database.sessions,
        run.scan_run_id,
        completed_count=len(results),
        failed_count=len(failures),
    )
    assert completed_run.completed_at is not None
    return ScannerResult(
        scan_run_id=run.scan_run_id,
        trigger=run.trigger,
        started_at=run.started_at,
        completed_at=completed_run.completed_at,
        attempted=len(symbols),
        results=tuple(results),
        failures=tuple(failures),
    )


@router.get("/scanner/runs", response_model=list[ScanRunView])
async def list_scan_runs(
    request: Request,
    context: WorkspaceContext = Depends(require_workspace),
) -> list[ScanRunView]:
    async with request.app.state.database.sessions() as session:
        records = list(
            await session.scalars(
                select(ConnectedScanRunRecord)
                .where(ConnectedScanRunRecord.workspace_id == context.workspace_id)
                .order_by(ConnectedScanRunRecord.started_at.desc())
                .limit(10)
            )
        )
    return [
        ScanRunView(
            scan_run_id=record.scan_run_id,
            trigger=record.trigger,
            source=record.source,
            started_at=record.started_at,
            completed_at=record.completed_at,
            attempted=record.attempted_count,
            completed=record.completed_count,
            failed=record.failed_count,
        )
        for record in records
    ]


@router.get("/scanner/runs/{scan_run_id}", response_model=list[ConnectedAnalysis])
async def get_scan_run_results(
    scan_run_id: UUID,
    request: Request,
    context: WorkspaceContext = Depends(require_workspace),
) -> list[ConnectedAnalysis]:
    async with request.app.state.database.sessions() as session:
        owned_run = await session.scalar(
            select(ConnectedScanRunRecord.scan_run_id).where(
                ConnectedScanRunRecord.scan_run_id == scan_run_id,
                ConnectedScanRunRecord.workspace_id == context.workspace_id,
            )
        )
        if owned_run is None:
            raise HTTPException(status_code=404, detail="Scan run not found")
        records = list(
            await session.scalars(
                select(ConnectedOpportunityRecord)
                .where(
                    ConnectedOpportunityRecord.workspace_id == context.workspace_id,
                    ConnectedOpportunityRecord.scan_run_id == scan_run_id,
                )
                .order_by(ConnectedOpportunityRecord.symbol)
            )
        )
    return [ConnectedAnalysis.model_validate(record.payload) for record in records]


@router.get("/opportunities", response_model=list[ConnectedAnalysis])
async def list_opportunities(
    request: Request, context: WorkspaceContext = Depends(require_workspace)
) -> list[ConnectedAnalysis]:
    async with request.app.state.database.sessions() as session:
        records = await session.scalars(
            select(ConnectedOpportunityRecord)
            .where(ConnectedOpportunityRecord.workspace_id == context.workspace_id)
            .order_by(ConnectedOpportunityRecord.created_at.desc())
            .limit(50)
        )
        return [ConnectedAnalysis.model_validate(record.payload) for record in records]


@router.get("/opportunities/{opportunity_id}", response_model=ConnectedAnalysis)
async def get_opportunity(
    opportunity_id: UUID,
    request: Request,
    context: WorkspaceContext = Depends(require_workspace),
) -> ConnectedAnalysis:
    async with request.app.state.database.sessions() as session:
        record = await session.scalar(
            select(ConnectedOpportunityRecord).where(
                ConnectedOpportunityRecord.workspace_id == context.workspace_id,
                ConnectedOpportunityRecord.opportunity_id == opportunity_id,
            )
        )
    if record is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return ConnectedAnalysis.model_validate(record.payload)


@router.post("/opportunities/{opportunity_id}/ai", response_model=AIWorkflowResult)
async def analyze_opportunity_with_ai(
    opportunity_id: UUID,
    request: Request,
    context: WorkspaceContext = Depends(require_workspace),
) -> AIWorkflowResult:
    async with request.app.state.database.sessions() as session:
        opportunity_record = await session.scalar(
            select(ConnectedOpportunityRecord).where(
                ConnectedOpportunityRecord.workspace_id == context.workspace_id,
                ConnectedOpportunityRecord.opportunity_id == opportunity_id,
            )
        )
    if opportunity_record is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    credential_store = _credential_store(request)
    credential = await credential_store.get(context.workspace_id, "OPENROUTER")
    secrets = await credential_store.reveal(context.workspace_id, "OPENROUTER")
    if credential is None or secrets is None or not credential.enabled:
        raise HTTPException(status_code=409, detail="Verified OpenRouter credentials required")
    model = str(credential.configuration.get("model", ""))
    provider = OpenRouterProvider(
        str(secrets["api_key"]),
        model=model,
        timeout_seconds=request.app.state.settings.ai_timeout_seconds,
    )
    opportunity = ConnectedAnalysis.model_validate(opportunity_record.payload)
    evidence: dict[str, object] = {
        "sources": [
            {"source_id": "alpaca-signal", "evidence": opportunity.signal},
            {"source_id": "alpaca-candidate", "evidence": opportunity.candidate},
            {"source_id": "deterministic-risk", "evidence": opportunity.risk_decision},
        ],
        "source": opportunity.source,
        "observed_at": opportunity.observed_at.isoformat(),
    }
    result = await AIWorkflow(provider).run(evidence)
    await AIWorkflowStore(request.app.state.database.sessions, context.workspace_id).save(
        correlation_id=opportunity_id,
        input_payload=evidence,
        result=result,
    )
    return result


@router.post("/opportunities/{opportunity_id}/confirm")
async def confirm_paper_order(
    opportunity_id: UUID,
    payload: ConfirmPaperOrder,
    request: Request,
    context: WorkspaceContext = Depends(require_workspace),
) -> BrokerOrder:
    async with request.app.state.database.sessions() as session:
        record = await session.scalar(
            select(ConnectedOpportunityRecord).where(
                ConnectedOpportunityRecord.workspace_id == context.workspace_id,
                ConnectedOpportunityRecord.opportunity_id == opportunity_id,
            )
        )
    if record is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opportunity = ConnectedAnalysis.model_validate(record.payload)
    if opportunity.source != "ALPACA_REAL" or opportunity.order_intent is None:
        raise HTTPException(
            status_code=409, detail="Only real, risk-approved intents can be confirmed"
        )
    if opportunity.expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=409, detail="Order review expired; analyze the symbol again"
        )
    intent = OrderIntent.model_validate(opportunity.order_intent)
    if payload.client_order_id != intent.client_order_id:
        raise HTTPException(
            status_code=409, detail="Confirmation does not match immutable order intent"
        )
    assert opportunity.candidate is not None
    candidate = RankedCandidate.model_validate(opportunity.candidate)
    projections = _broker_store(request, context)
    account = await projections.get_account()
    if account is None:
        raise HTTPException(status_code=409, detail="Broker account projection unavailable")
    positions = await projections.list_positions()
    gate = await BrokerExecutionGate(projections).evaluate()
    rerisk = RiskEngine(RiskPolicy()).evaluate(
        candidate,
        RiskContext(
            paper_equity=account.equity,
            open_planned_loss=0,
            underlying_open_risk=0,
            daily_loss=max(account.last_equity - account.equity, Decimal("0")),
            drawdown_percent=max(account.last_equity - account.equity, Decimal("0"))
            / max(account.last_equity, Decimal("1"))
            * Decimal("100"),
            concurrent_option_structures=len(positions),
            broker_execution_allowed=gate.allowed,
        ),
    )
    if rerisk.decision != "APPROVE":
        raise HTTPException(
            status_code=409, detail="Deterministic risk no longer approves this order"
        )
    secrets = await _credential_store(request).reveal(context.workspace_id, "ALPACA")
    if secrets is None:
        raise HTTPException(status_code=409, detail="Alpaca credential unavailable")
    adapter = AlpacaPaperBrokerAdapter(str(secrets["api_key_id"]), str(secrets["secret_key"]))
    guardian = PostgresGuardianStore(request.app.state.database.sessions, context.workspace_id)
    engine = ExecutionEngine(
        adapter,
        PostgresIntentStore(request.app.state.database.sessions, context.workspace_id),
        preflight=ConnectedPreflight(
            BrokerExecutionGate(projections), GuardianExecutionGate(guardian)
        ),
    )
    try:
        return await engine.execute(intent)
    except ExecutionBlocked as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    finally:
        await adapter.close()


def _broker_store(request: Request, context: WorkspaceContext) -> PostgresBrokerProjectionStore:
    return PostgresBrokerProjectionStore(request.app.state.database.sessions, context.workspace_id)


@router.get("/broker/status")
async def broker_status(
    request: Request, context: WorkspaceContext = Depends(require_workspace)
) -> BrokerSyncStatus:
    return await _broker_store(request, context).get_status()


@router.get("/broker/account")
async def broker_account(
    request: Request, context: WorkspaceContext = Depends(require_workspace)
) -> BrokerAccount | None:
    return await _broker_store(request, context).get_account()


@router.get("/broker/positions")
async def broker_positions(
    request: Request, context: WorkspaceContext = Depends(require_workspace)
) -> tuple[BrokerPosition, ...]:
    return await _broker_store(request, context).list_positions()


@router.post("/broker/positions/{symbol_or_asset_id}/close", response_model=BrokerOrder)
async def close_position(
    symbol_or_asset_id: str,
    request: Request,
    context: WorkspaceContext = Depends(require_workspace),
) -> BrokerOrder:
    secrets = await _credential_store(request).reveal(context.workspace_id, "ALPACA")
    if secrets is None:
        raise HTTPException(status_code=409, detail="Alpaca credential unavailable")
    adapter = AlpacaPaperBrokerAdapter(str(secrets["api_key_id"]), str(secrets["secret_key"]))
    try:
        order = await adapter.close_position(symbol_or_asset_id)
        projections = _broker_store(request, context)
        snapshot = await adapter.reconcile()
        await projections.save_snapshot(snapshot)
        return order
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    finally:
        await adapter.close()


@router.get("/broker/orders")
async def broker_orders(
    request: Request, context: WorkspaceContext = Depends(require_workspace)
) -> tuple[BrokerOrder, ...]:
    return await _broker_store(request, context).list_orders()


@router.get("/guardian/status", response_model=GuardianStatus)
async def guardian_status(
    request: Request, context: WorkspaceContext = Depends(require_workspace)
) -> GuardianStatus:
    return await PostgresGuardianStore(
        request.app.state.database.sessions, context.workspace_id
    ).status()


@router.post("/guardian/halt", response_model=GuardianStatus)
async def guardian_halt(
    request: Request, context: WorkspaceContext = Depends(require_workspace)
) -> GuardianStatus:
    guardian = PostgresGuardianStore(request.app.state.database.sessions, context.workspace_id)
    await guardian.halt(
        (GuardianTrigger.MANUAL_KILL_SWITCH,),
        "Operator activated the connected paper kill switch.",
    )
    return await guardian.status()


@router.post("/guardian/recover", response_model=GuardianStatus)
async def guardian_recover(
    request: Request, context: WorkspaceContext = Depends(require_workspace)
) -> GuardianStatus:
    broker = _broker_store(request, context)
    status = await broker.get_status()
    fresh = status.last_reconciled_at is not None and datetime.now(
        UTC
    ) - status.last_reconciled_at <= timedelta(seconds=90)
    known = status.state is BrokerState.RECONCILED and status.stream_connected and fresh
    guardian = PostgresGuardianStore(request.app.state.database.sessions, context.workspace_id)
    try:
        return await guardian.recover(broker_state_known=known)
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
