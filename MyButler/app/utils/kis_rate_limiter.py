# -*- coding: utf-8 -*-
"""
KIS Rate Limiter
한국투자증권 API 호출 제한 관리
"""
import logging
import threading
import time
from collections import deque
from functools import lru_cache

logger = logging.getLogger(__name__)


class KISRateLimiter:
    """
    KIS API 호출 속도 제한기

    - 초당 최대 호출 수 제한
    - 스레드 안전
    """

    def __init__(self, calls_per_second: int = 15):
        """
        초기화

        Args:
            calls_per_second: 초당 최대 호출 수 (기본값: 15, API 제한 20 대비 여유)
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self._call_times = deque(maxlen=calls_per_second)
        self._lock = threading.Lock()

    def wait_if_needed(self):
        """
        호출 전 필요시 대기

        초당 호출 제한을 초과하지 않도록 대기합니다.
        """
        with self._lock:
            now = time.time()

            # 1초 이전 기록 제거
            while self._call_times and (now - self._call_times[0]) >= 1.0:
                self._call_times.popleft()

            # 호출 횟수가 제한에 도달하면 대기
            if len(self._call_times) >= self.calls_per_second:
                oldest = self._call_times[0]
                wait_time = 1.0 - (now - oldest)
                if wait_time > 0:
                    logger.debug(f"Rate limit 도달, {wait_time:.3f}초 대기")
                    time.sleep(wait_time)

            # 호출 시간 기록
            self._call_times.append(time.time())

    def smart_sleep(self, seconds: float = 0.1):
        """
        호출 후 안전 대기

        Args:
            seconds: 대기 시간 (기본값: 0.1초)
        """
        time.sleep(seconds)

    def reset(self):
        """호출 기록 초기화"""
        with self._lock:
            self._call_times.clear()


@lru_cache()
def get_rate_limiter() -> KISRateLimiter:
    """Rate Limiter 싱글톤"""
    return KISRateLimiter()
