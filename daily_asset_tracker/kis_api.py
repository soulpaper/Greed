import requests
import json
import logging
from datetime import datetime, timedelta
from daily_asset_tracker.config import settings

logger = logging.getLogger(__name__)

class KISClient:
    def __init__(self):
        self.base_url = settings.KIS_BASE_URL
        self.app_key = settings.KIS_APP_KEY
        self.app_secret = settings.KIS_APP_SECRET
        self.cano = settings.KIS_CANO
        self.acnt_prdt_cd = settings.KIS_ACNT_PRDT_CD
        self.access_token = None
        self.token_issued_at = None
        self.token_expiry_duration = timedelta(hours=23)  # 토큰 유효기간을 안전하게 23시간으로 설정

    def _get_access_token(self):
        # 토큰이 없거나 만료되었으면 재발급
        if self.access_token and self.token_issued_at:
            if datetime.now() - self.token_issued_at < self.token_expiry_duration:
                return self.access_token
            else:
                logger.info("Access token expired. Refreshing...")

        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(body))
            response.raise_for_status()
            data = response.json()
            self.access_token = data["access_token"]
            self.token_issued_at = datetime.now()
            logger.info("KIS API Access Token issued successfully.")
            return self.access_token
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            raise

    def get_headers(self, tr_id, tr_cont=""):
        token = self._get_access_token()
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P" # 개인
        }
        if tr_cont:
            headers["tr_cont"] = tr_cont
        return headers

    def inquire_balance(self):
        """
        주식 잔고 조회 (실전: TTTC8434R)
        페이지네이션(연속조회) 지원
        """
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        tr_id = "TTTC8434R"

        # 초기 파라미터
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02", # 종목별
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }

        all_holdings = [] # output1 누적
        account_summary = {} # output2 (마지막 응답 기준)

        tr_cont_req = "" # 초기 요청은 공백

        while True:
            headers = self.get_headers(tr_id, tr_cont=tr_cont_req)
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                if data['rt_cd'] != '0':
                    logger.error(f"API Error: {data['msg1']}")
                    raise Exception(f"API Error: {data['msg1']}")

                # 데이터 누적
                output1 = data.get('output1', [])
                if output1:
                    all_holdings.extend(output1)

                # 계좌 요약 정보 갱신
                output2 = data.get('output2', [])
                if output2:
                    account_summary = output2[0] if isinstance(output2, list) else output2

                # 연속 조회 체크
                tr_cont_res = response.headers.get('tr_cont', 'N')

                # 다음 페이지가 없으면(M이나 F가 아니면) 종료
                if tr_cont_res not in ['M', 'F']:
                     break

                # 다음 요청을 위한 설정
                tr_cont_req = "N" # 연속 조회 시 헤더에 N 설정 (KIS API 스펙)
                params["CTX_AREA_FK100"] = data.get("ctx_area_fk100", "")
                params["CTX_AREA_NK100"] = data.get("ctx_area_nk100", "")

                # 무한 루프 방지용 (키가 없으면 종료)
                if not params["CTX_AREA_NK100"].strip():
                    break

                logger.info("Fetching next page of holdings...")

            except Exception as e:
                logger.error(f"Failed to inquire balance: {e}")
                raise

        return {
            "output1": all_holdings,
            "output2": [account_summary] if account_summary else []
        }

kis_client = KISClient()
