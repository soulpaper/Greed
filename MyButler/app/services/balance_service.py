# -*- coding: utf-8 -*-
"""
Balance Service
주식 잔고 조회 서비스 (해외/국내)
"""
import logging
from functools import lru_cache
from typing import Optional, Tuple

import pandas as pd

from app.utils.kis_auth_manager import get_auth_manager, KISAuthManager
from app.utils.kis_rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

# 해외주식 API 상수
OVERSEAS_API_URL = "/uapi/overseas-stock/v1/trading/inquire-balance"
OVERSEAS_TR_ID_REAL = "TTTS3012R"  # 실전투자용
OVERSEAS_TR_ID_DEMO = "VTTS3012R"  # 모의투자용

# 국내주식 API 상수
DOMESTIC_API_URL = "/uapi/domestic-stock/v1/trading/inquire-balance"
DOMESTIC_TR_ID_REAL = "TTTC8434R"  # 실전투자용
DOMESTIC_TR_ID_DEMO = "VTTC8434R"  # 모의투자용


class BalanceService:
    """주식 잔고 조회 서비스 (해외/국내)"""

    def __init__(self, auth_manager: Optional[KISAuthManager] = None):
        """
        초기화

        Args:
            auth_manager: KIS 인증 매니저 (기본값: 싱글톤)
        """
        self._auth = auth_manager or get_auth_manager()
        self._rate_limiter = get_rate_limiter()

    def get_overseas_balance(
        self,
        ovrs_excg_cd: str,
        tr_crcy_cd: str,
        max_pages: int = 10,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        해외주식 잔고 조회 (동기)

        Args:
            ovrs_excg_cd: 해외거래소코드 (NASD, NYSE, AMEX, TKSE 등)
            tr_crcy_cd: 거래통화코드 (USD, JPY 등)
            max_pages: 최대 페이지 수 (기본값: 10)

        Returns:
            Tuple[DataFrame, DataFrame]:
                - stocks_df: 종목별 잔고 데이터
                - summary_df: 계좌 요약 데이터
        """
        return self._fetch_balance(
            ovrs_excg_cd=ovrs_excg_cd,
            tr_crcy_cd=tr_crcy_cd,
            max_pages=max_pages,
        )

    async def get_overseas_balance_async(
        self,
        ovrs_excg_cd: str,
        tr_crcy_cd: str,
        max_pages: int = 10,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        해외주식 잔고 조회 (비동기)

        Args:
            ovrs_excg_cd: 해외거래소코드
            tr_crcy_cd: 거래통화코드
            max_pages: 최대 페이지 수

        Returns:
            Tuple[DataFrame, DataFrame]:
                - stocks_df: 종목별 잔고 데이터
                - summary_df: 계좌 요약 데이터
        """
        return await self._fetch_balance_async(
            ovrs_excg_cd=ovrs_excg_cd,
            tr_crcy_cd=tr_crcy_cd,
            max_pages=max_pages,
        )

    def _fetch_balance(
        self,
        ovrs_excg_cd: str,
        tr_crcy_cd: str,
        max_pages: int,
        fk200: str = "",
        nk200: str = "",
        tr_cont: str = "",
        stocks_df: Optional[pd.DataFrame] = None,
        summary_df: Optional[pd.DataFrame] = None,
        page: int = 0,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """잔고 조회 내부 구현 (페이지네이션 처리)"""
        if page >= max_pages:
            logger.warning(f"최대 페이지 수({max_pages}) 도달")
            return stocks_df or pd.DataFrame(), summary_df or pd.DataFrame()

        params = {
            "CANO": self._auth.account_number,
            "ACNT_PRDT_CD": self._auth.product_code,
            "OVRS_EXCG_CD": ovrs_excg_cd,
            "TR_CRCY_CD": tr_crcy_cd,
            "CTX_AREA_FK200": fk200,
            "CTX_AREA_NK200": nk200,
        }

        response = self._auth.api_call(
            api_url=OVERSEAS_API_URL,
            tr_id=OVERSEAS_TR_ID_REAL,
            params=params,
            tr_cont=tr_cont,
        )

        if not response.is_ok():
            response.print_error(OVERSEAS_API_URL)
            logger.error(f"해외주식 잔고 조회 실패: {response.error_code} - {response.error_message}")
            return pd.DataFrame(), pd.DataFrame()

        # output1: 종목별 잔고
        stocks_df = self._process_output(response.output1, stocks_df)

        # output2: 계좌 요약
        summary_df = self._process_output(response.output2, summary_df)

        # 연속 조회 처리
        next_tr_cont = response.tr_cont
        next_fk200 = response.ctx_area_fk200
        next_nk200 = response.ctx_area_nk200

        if next_tr_cont in ["M", "F"]:
            logger.info(f"다음 페이지 조회 (page={page + 1})")
            self._rate_limiter.smart_sleep()
            return self._fetch_balance(
                ovrs_excg_cd=ovrs_excg_cd,
                tr_crcy_cd=tr_crcy_cd,
                max_pages=max_pages,
                fk200=next_fk200,
                nk200=next_nk200,
                tr_cont="N",
                stocks_df=stocks_df,
                summary_df=summary_df,
                page=page + 1,
            )

        logger.info(f"해외주식 잔고 조회 완료: {ovrs_excg_cd} ({tr_crcy_cd}) - {len(stocks_df)}개 종목")
        return stocks_df, summary_df

    async def _fetch_balance_async(
        self,
        ovrs_excg_cd: str,
        tr_crcy_cd: str,
        max_pages: int,
        fk200: str = "",
        nk200: str = "",
        tr_cont: str = "",
        stocks_df: Optional[pd.DataFrame] = None,
        summary_df: Optional[pd.DataFrame] = None,
        page: int = 0,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """잔고 조회 비동기 내부 구현"""
        if page >= max_pages:
            logger.warning(f"최대 페이지 수({max_pages}) 도달")
            return stocks_df or pd.DataFrame(), summary_df or pd.DataFrame()

        params = {
            "CANO": self._auth.account_number,
            "ACNT_PRDT_CD": self._auth.product_code,
            "OVRS_EXCG_CD": ovrs_excg_cd,
            "TR_CRCY_CD": tr_crcy_cd,
            "CTX_AREA_FK200": fk200,
            "CTX_AREA_NK200": nk200,
        }

        response = await self._auth.api_call_async(
            api_url=OVERSEAS_API_URL,
            tr_id=OVERSEAS_TR_ID_REAL,
            params=params,
            tr_cont=tr_cont,
        )

        if not response.is_ok():
            response.print_error(OVERSEAS_API_URL)
            logger.error(f"해외주식 잔고 조회 실패: {response.error_code} - {response.error_message}")
            return pd.DataFrame(), pd.DataFrame()

        # output1: 종목별 잔고
        stocks_df = self._process_output(response.output1, stocks_df)

        # output2: 계좌 요약
        summary_df = self._process_output(response.output2, summary_df)

        # 연속 조회 처리
        next_tr_cont = response.tr_cont
        next_fk200 = response.ctx_area_fk200
        next_nk200 = response.ctx_area_nk200

        if next_tr_cont in ["M", "F"]:
            logger.info(f"다음 페이지 조회 (page={page + 1})")
            self._rate_limiter.smart_sleep()
            return await self._fetch_balance_async(
                ovrs_excg_cd=ovrs_excg_cd,
                tr_crcy_cd=tr_crcy_cd,
                max_pages=max_pages,
                fk200=next_fk200,
                nk200=next_nk200,
                tr_cont="N",
                stocks_df=stocks_df,
                summary_df=summary_df,
                page=page + 1,
            )

        logger.info(f"해외주식 잔고 조회 완료: {ovrs_excg_cd} ({tr_crcy_cd}) - {len(stocks_df)}개 종목")
        return stocks_df, summary_df

    def _process_output(
        self,
        output_data: any,
        existing_df: Optional[pd.DataFrame],
    ) -> pd.DataFrame:
        """API 출력 데이터를 DataFrame으로 처리"""
        if not output_data:
            return existing_df if existing_df is not None else pd.DataFrame()

        # 리스트가 아니면 리스트로 변환
        if not isinstance(output_data, list):
            output_data = [output_data]

        current_df = pd.DataFrame(output_data)

        if existing_df is not None and not existing_df.empty:
            return pd.concat([existing_df, current_df], ignore_index=True)

        return current_df

    # ========== 국내주식 잔고 조회 ==========

    def get_domestic_balance(
        self,
        max_pages: int = 10,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        국내주식 잔고 조회 (동기)

        Args:
            max_pages: 최대 페이지 수 (기본값: 10)

        Returns:
            Tuple[DataFrame, DataFrame]:
                - stocks_df: 종목별 잔고 데이터
                - summary_df: 계좌 요약 데이터
        """
        return self._fetch_domestic_balance(max_pages=max_pages)

    async def get_domestic_balance_async(
        self,
        max_pages: int = 10,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        국내주식 잔고 조회 (비동기)

        Args:
            max_pages: 최대 페이지 수

        Returns:
            Tuple[DataFrame, DataFrame]:
                - stocks_df: 종목별 잔고 데이터
                - summary_df: 계좌 요약 데이터
        """
        return await self._fetch_domestic_balance_async(max_pages=max_pages)

    def _fetch_domestic_balance(
        self,
        max_pages: int,
        fk100: str = "",
        nk100: str = "",
        tr_cont: str = "",
        stocks_df: Optional[pd.DataFrame] = None,
        summary_df: Optional[pd.DataFrame] = None,
        page: int = 0,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """국내주식 잔고 조회 내부 구현"""
        if page >= max_pages:
            logger.warning(f"최대 페이지 수({max_pages}) 도달")
            return stocks_df or pd.DataFrame(), summary_df or pd.DataFrame()

        params = {
            "CANO": self._auth.account_number,
            "ACNT_PRDT_CD": self._auth.product_code,
            "AFHR_FLPR_YN": "N",  # 시간외단일가 여부
            "OFL_YN": "",
            "INQR_DVSN": "02",  # 종목별 조회
            "UNPR_DVSN": "01",  # 단가구분
            "FUND_STTL_ICLD_YN": "N",  # 펀드결제분 포함여부
            "FNCG_AMT_AUTO_RDPT_YN": "N",  # 융자금액자동상환여부
            "PRCS_DVSN": "00",  # 전일매매포함
            "CTX_AREA_FK100": fk100,
            "CTX_AREA_NK100": nk100,
        }

        response = self._auth.api_call(
            api_url=DOMESTIC_API_URL,
            tr_id=DOMESTIC_TR_ID_REAL,
            params=params,
            tr_cont=tr_cont,
        )

        if not response.is_ok():
            response.print_error(DOMESTIC_API_URL)
            logger.error(f"국내주식 잔고 조회 실패: {response.error_code} - {response.error_message}")
            return pd.DataFrame(), pd.DataFrame()

        # output1: 종목별 잔고
        stocks_df = self._process_output(response.output1, stocks_df)

        # output2: 계좌 요약
        summary_df = self._process_output(response.output2, summary_df)

        # 연속 조회 처리 (국내주식은 FK100/NK100 사용)
        next_tr_cont = response.tr_cont
        next_fk100 = response.body.get("ctx_area_fk100", "")
        next_nk100 = response.body.get("ctx_area_nk100", "")

        if next_tr_cont in ["M", "F"]:
            logger.info(f"다음 페이지 조회 (page={page + 1})")
            self._rate_limiter.smart_sleep()
            return self._fetch_domestic_balance(
                max_pages=max_pages,
                fk100=next_fk100,
                nk100=next_nk100,
                tr_cont="N",
                stocks_df=stocks_df,
                summary_df=summary_df,
                page=page + 1,
            )

        logger.info(f"국내주식 잔고 조회 완료: {len(stocks_df)}개 종목")
        return stocks_df, summary_df

    async def _fetch_domestic_balance_async(
        self,
        max_pages: int,
        fk100: str = "",
        nk100: str = "",
        tr_cont: str = "",
        stocks_df: Optional[pd.DataFrame] = None,
        summary_df: Optional[pd.DataFrame] = None,
        page: int = 0,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """국내주식 잔고 조회 비동기 내부 구현"""
        if page >= max_pages:
            logger.warning(f"최대 페이지 수({max_pages}) 도달")
            return stocks_df or pd.DataFrame(), summary_df or pd.DataFrame()

        params = {
            "CANO": self._auth.account_number,
            "ACNT_PRDT_CD": self._auth.product_code,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": fk100,
            "CTX_AREA_NK100": nk100,
        }

        response = await self._auth.api_call_async(
            api_url=DOMESTIC_API_URL,
            tr_id=DOMESTIC_TR_ID_REAL,
            params=params,
            tr_cont=tr_cont,
        )

        if not response.is_ok():
            response.print_error(DOMESTIC_API_URL)
            logger.error(f"국내주식 잔고 조회 실패: {response.error_code} - {response.error_message}")
            return pd.DataFrame(), pd.DataFrame()

        # output1: 종목별 잔고
        stocks_df = self._process_output(response.output1, stocks_df)

        # output2: 계좌 요약
        summary_df = self._process_output(response.output2, summary_df)

        # 연속 조회 처리
        next_tr_cont = response.tr_cont
        next_fk100 = response.body.get("ctx_area_fk100", "")
        next_nk100 = response.body.get("ctx_area_nk100", "")

        if next_tr_cont in ["M", "F"]:
            logger.info(f"다음 페이지 조회 (page={page + 1})")
            self._rate_limiter.smart_sleep()
            return await self._fetch_domestic_balance_async(
                max_pages=max_pages,
                fk100=next_fk100,
                nk100=next_nk100,
                tr_cont="N",
                stocks_df=stocks_df,
                summary_df=summary_df,
                page=page + 1,
            )

        logger.info(f"국내주식 잔고 조회 완료: {len(stocks_df)}개 종목")
        return stocks_df, summary_df


@lru_cache()
def get_balance_service() -> BalanceService:
    """잔고 서비스 싱글톤"""
    return BalanceService()
