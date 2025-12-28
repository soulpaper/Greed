import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from daily_asset_tracker.models import Base, AccountSnapshot, StockHolding
from daily_asset_tracker.service import fetch_and_save_account_status
from daily_asset_tracker.kis_api import KISClient

# 테스트용 인메모리 SQLite DB 설정
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

class TestDailyAssetTracker(unittest.TestCase):
    def setUp(self):
        # 테스트 데이터베이스 테이블 생성
        Base.metadata.create_all(bind=test_engine)
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=test_engine)

    @patch('daily_asset_tracker.service.SessionLocal')
    @patch('daily_asset_tracker.service.kis_client')
    def test_fetch_and_save(self, mock_kis_client, mock_session_local):
        # SessionLocal이 호출되면 테스트용 세션을 반환하도록 설정
        mock_session_local.return_value = self.db

        # API 응답 Mocking (페이지네이션 된 결과라고 가정)
        mock_response = {
            'rt_cd': '0',
            'output1': [
                {
                    'pdno': '005930',
                    'prdt_name': '삼성전자',
                    'hldg_qty': '10',
                    'pchs_avg_pric': '70000',
                    'prpr': '72000',
                    'evlu_amt': '720000',
                    'evlu_pfls_amt': '20000',
                    'evlu_pfls_rt': '2.85'
                },
                {
                    'pdno': '000660',
                    'prdt_name': 'SK하이닉스',
                    'hldg_qty': '5',
                    'pchs_avg_pric': '120000',
                    'prpr': '125000',
                    'evlu_amt': '625000',
                    'evlu_pfls_amt': '25000',
                    'evlu_pfls_rt': '4.17'
                }
            ],
            'output2': [
                {
                    'tot_evlu_amt': '1345000',
                    'dnca_tot_amt': '280000',
                    'pchs_amt_smtl_amt': '1300000',
                    'evlu_pfls_smtl_amt': '45000'
                }
            ]
        }
        mock_kis_client.inquire_balance.return_value = mock_response

        # 서비스 함수 실행
        fetch_and_save_account_status()

        # DB 확인
        snapshot = self.db.query(AccountSnapshot).first()
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.total_asset_amount, 1345000)

        holdings = self.db.query(StockHolding).filter_by(snapshot_id=snapshot.id).all()
        self.assertEqual(len(holdings), 2)
        self.assertEqual(holdings[0].prdt_name, '삼성전자')
        self.assertEqual(holdings[1].prdt_name, 'SK하이닉스')

    @patch('daily_asset_tracker.kis_api.requests.post')
    def test_token_refresh(self, mock_post):
        # KISClient 토큰 갱신 테스트
        client = KISClient()
        client.access_token = "old_token"
        client.token_issued_at = datetime.now() - timedelta(hours=24) # 24시간 지남

        # Mock Response for Token
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "new_token",
            "token_type": "Bearer",
            "expires_in": 86400
        }

        # 호출 시 토큰 갱신이 일어나야 함
        token = client._get_access_token()

        self.assertEqual(token, "new_token")
        self.assertEqual(client.access_token, "new_token")
        self.assertTrue(datetime.now() - client.token_issued_at < timedelta(seconds=1))

if __name__ == '__main__':
    unittest.main()
