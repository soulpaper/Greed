# -*- coding: utf-8 -*-
"""
KIS API 인증 매니저
한국투자증권 OpenAPI 인증 및 API 호출 관리
"""
import asyncio
import copy
import json
import logging
import os
import time
from collections import namedtuple
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp
import requests
import yaml

from app.utils.kis_rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class KISAuthManager:
    """KIS API 인증 관리자"""

    BASE_URL = "https://openapi.koreainvestment.com:9443"

    def __init__(self, config_path: Optional[str] = None):
        """
        초기화

        Args:
            config_path: config.yaml 경로 (기본값: 프로젝트 루트의 config.yaml)
        """
        if config_path is None:
            # MyButler 프로젝트 루트에서 config.yaml 찾기
            config_path = Path(__file__).parent.parent.parent / "config.yaml"

        self._load_config(config_path)
        self._setup_cache_dir()
        self._token: Optional[str] = None
        self._token_expired: Optional[datetime] = None
        self._rate_limiter = get_rate_limiter()

        # 기본 헤더
        self._base_headers = {
            "Content-Type": "application/json",
            "Accept": "text/plain",
            "charset": "UTF-8",
            "User-Agent": self._config.get("my_agent", "Mozilla/5.0"),
        }

    def _load_config(self, config_path: Path):
        """설정 파일 로드"""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")

        with open(config_path, encoding="UTF-8") as f:
            self._config = yaml.safe_load(f)

        # 필수 설정 확인
        required_keys = ["my_app", "my_sec", "my_acct_stock", "my_prod"]
        for key in required_keys:
            if key not in self._config:
                raise ValueError(f"설정 파일에 '{key}' 항목이 없습니다")

        logger.info("KIS 설정 로드 완료")

    def _setup_cache_dir(self):
        """토큰 캐시 디렉토리 설정"""
        self._cache_dir = Path.home() / ".kis_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._token_file = self._cache_dir / f"token_{self._config['my_acct_stock']}.json"

    def _load_cached_token(self) -> Optional[str]:
        """캐시된 토큰 로드"""
        if not self._token_file.exists():
            return None

        try:
            with open(self._token_file, encoding="UTF-8") as f:
                cache = json.load(f)

            expired = datetime.fromisoformat(cache["expired"])
            if expired > datetime.now():
                self._token = cache["token"]
                self._token_expired = expired
                logger.debug(f"캐시된 토큰 사용 (만료: {expired})")
                return self._token
            else:
                logger.debug("캐시된 토큰 만료됨")
                return None
        except Exception as e:
            logger.warning(f"토큰 캐시 로드 실패: {e}")
            return None

    def _save_token_cache(self, token: str, expired: datetime):
        """토큰 캐시 저장"""
        try:
            cache = {
                "token": token,
                "expired": expired.isoformat(),
                "created": datetime.now().isoformat(),
            }
            with open(self._token_file, "w", encoding="UTF-8") as f:
                json.dump(cache, f, indent=2)
            logger.debug(f"토큰 캐시 저장 완료: {self._token_file}")
        except Exception as e:
            logger.warning(f"토큰 캐시 저장 실패: {e}")

    def _request_new_token(self) -> str:
        """새 토큰 발급 요청"""
        url = f"{self.BASE_URL}/oauth2/tokenP"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self._config["my_app"],
            "appsecret": self._config["my_sec"],
        }

        logger.info("새 토큰 발급 요청 중... (알림톡이 발송됩니다)")

        response = requests.post(url, json=payload, headers=self._base_headers)

        if response.status_code != 200:
            raise RuntimeError(f"토큰 발급 실패: {response.status_code} - {response.text}")

        data = response.json()
        token = data["access_token"]
        expired_str = data["access_token_token_expired"]
        expired = datetime.strptime(expired_str, "%Y-%m-%d %H:%M:%S")

        self._token = token
        self._token_expired = expired
        self._save_token_cache(token, expired)

        logger.info(f"토큰 발급 완료 (만료: {expired})")
        return token

    def ensure_authenticated(self) -> str:
        """
        인증 확인/갱신

        Returns:
            유효한 액세스 토큰
        """
        # 캐시된 토큰 확인
        if self._token and self._token_expired:
            if self._token_expired > datetime.now():
                return self._token

        # 파일 캐시에서 로드 시도
        cached = self._load_cached_token()
        if cached:
            return cached

        # 새 토큰 발급
        return self._request_new_token()

    def get_headers(self, tr_id: str, tr_cont: str = "") -> Dict[str, str]:
        """
        API 호출용 헤더 생성

        Args:
            tr_id: 거래 ID (예: TTTS3012R)
            tr_cont: 연속 거래 여부 (빈 문자열, "N", "M", "F")

        Returns:
            API 호출용 헤더
        """
        token = self.ensure_authenticated()

        headers = copy.deepcopy(self._base_headers)
        headers["authorization"] = f"Bearer {token}"
        headers["appkey"] = self._config["my_app"]
        headers["appsecret"] = self._config["my_sec"]
        headers["tr_id"] = tr_id
        headers["custtype"] = "P"  # 개인고객

        if tr_cont:
            headers["tr_cont"] = tr_cont

        return headers

    @property
    def account_number(self) -> str:
        """계좌번호 앞 8자리"""
        return self._config["my_acct_stock"]

    @property
    def product_code(self) -> str:
        """계좌상품코드 뒤 2자리"""
        return self._config["my_prod"]

    def api_call(
        self,
        api_url: str,
        tr_id: str,
        params: Dict[str, Any],
        tr_cont: str = "",
        method: str = "GET",
    ) -> "APIResponse":
        """
        동기 API 호출

        Args:
            api_url: API URL (예: /uapi/overseas-stock/v1/trading/inquire-balance)
            tr_id: 거래 ID
            params: 요청 파라미터
            tr_cont: 연속 거래 여부
            method: HTTP 메서드 (GET/POST)

        Returns:
            APIResponse 객체
        """
        url = f"{self.BASE_URL}{api_url}"
        headers = self.get_headers(tr_id, tr_cont)

        # Rate Limiter 적용
        self._rate_limiter.wait_if_needed()

        try:
            if method.upper() == "POST":
                response = requests.post(url, headers=headers, json=params)
            else:
                response = requests.get(url, headers=headers, params=params)

            return APIResponse(response)

        except Exception as e:
            logger.error(f"API 호출 오류: {e}")
            return APIResponseError(0, str(e))

    async def api_call_async(
        self,
        api_url: str,
        tr_id: str,
        params: Dict[str, Any],
        tr_cont: str = "",
        method: str = "GET",
    ) -> "APIResponse":
        """
        비동기 API 호출

        Args:
            api_url: API URL
            tr_id: 거래 ID
            params: 요청 파라미터
            tr_cont: 연속 거래 여부
            method: HTTP 메서드 (GET/POST)

        Returns:
            APIResponse 객체
        """
        url = f"{self.BASE_URL}{api_url}"
        headers = self.get_headers(tr_id, tr_cont)

        # Rate Limiter 적용 (동기적으로)
        self._rate_limiter.wait_if_needed()

        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == "POST":
                    async with session.post(url, headers=headers, json=params) as response:
                        status = response.status
                        data = await response.json()
                        resp_headers = dict(response.headers)
                else:
                    async with session.get(url, headers=headers, params=params) as response:
                        status = response.status
                        data = await response.json()
                        resp_headers = dict(response.headers)

                return APIResponse.from_async(status, data, resp_headers)

        except Exception as e:
            logger.error(f"비동기 API 호출 오류: {e}")
            return APIResponseError(0, str(e))


class APIResponse:
    """API 응답 래퍼"""

    def __init__(self, response: requests.Response):
        self._status_code = response.status_code
        self._response = response
        self._data = response.json() if response.status_code == 200 else {}
        self._headers = dict(response.headers)

    @classmethod
    def from_async(cls, status_code: int, data: dict, headers: dict) -> "APIResponse":
        """비동기 응답으로부터 생성"""
        instance = cls.__new__(cls)
        instance._status_code = status_code
        instance._response = None
        instance._data = data
        instance._headers = headers
        return instance

    def is_ok(self) -> bool:
        """응답 성공 여부"""
        if self._status_code != 200:
            return False
        return self._data.get("rt_cd") == "0"

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def body(self) -> Dict[str, Any]:
        """응답 본문"""
        return self._data

    @property
    def output1(self) -> Any:
        """output1 데이터"""
        return self._data.get("output1")

    @property
    def output2(self) -> Any:
        """output2 데이터"""
        return self._data.get("output2")

    @property
    def tr_cont(self) -> str:
        """연속 거래 여부"""
        # 헤더에서 소문자로 찾기
        for key in self._headers:
            if key.lower() == "tr_cont":
                return self._headers[key]
        return ""

    @property
    def ctx_area_fk200(self) -> str:
        """연속조회검색조건200"""
        return self._data.get("ctx_area_fk200", "")

    @property
    def ctx_area_nk200(self) -> str:
        """연속조회키200"""
        return self._data.get("ctx_area_nk200", "")

    @property
    def error_code(self) -> str:
        """에러 코드"""
        return self._data.get("msg_cd", "")

    @property
    def error_message(self) -> str:
        """에러 메시지"""
        return self._data.get("msg1", "")

    def print_error(self, url: str = ""):
        """에러 출력"""
        logger.error(
            f"API 오류 - URL: {url}, Code: {self.error_code}, Message: {self.error_message}"
        )


class APIResponseError(APIResponse):
    """API 오류 응답"""

    def __init__(self, status_code: int, error_text: str):
        self._status_code = status_code
        self._response = None
        self._data = {}
        self._headers = {}
        self._error_text = error_text

    def is_ok(self) -> bool:
        return False

    @property
    def error_message(self) -> str:
        return self._error_text


@lru_cache()
def get_auth_manager() -> KISAuthManager:
    """KIS 인증 매니저 싱글톤"""
    return KISAuthManager()
