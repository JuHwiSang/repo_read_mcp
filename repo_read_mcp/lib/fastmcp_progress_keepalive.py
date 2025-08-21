# keepalive_progress.py
from fastmcp import Context
import asyncio, random, contextlib
from typing import Optional

async def start_progress_keepalive(
    ctx: Context,
    *,
    interval: float = 30.0,   # 한 번에 20~60초 권장
    jitter: float = 5.0,      # ±5초 지터로 동시 폭주/패턴화 방지
) -> asyncio.Task:
    """
    indeterminate progress(총합 없이)로 주기적 하트비트를 보내 세션 유지를 돕는다.
    반환된 task는 작업 종료 시 반드시 cancel() 해줄 것.
    """
    tick = 0

    async def _loop():
        nonlocal tick
        while True:
            tick = (tick + 1) if tick < 1_000_000 else 1
            # total 없이 progress만(아주 작은 payload). UI에선 '진행 중' 신호로 처리됨.
            await ctx.report_progress(progress=tick)
            # interval ± jitter
            sleep_for = max(0.1, interval + (random.random() - 0.5) * 2 * jitter)
            await asyncio.sleep(sleep_for)

    return asyncio.create_task(_loop())


class ProgressKeepAlive:
    """async with 로 쓰고 싶을 때"""
    def __init__(self, ctx: Context, *, interval: float = 30.0, jitter: float = 5.0):
        self.ctx = ctx
        self.interval = interval
        self.jitter = jitter
        self._task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        self._task = await start_progress_keepalive(self.ctx, interval=self.interval, jitter=self.jitter)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
