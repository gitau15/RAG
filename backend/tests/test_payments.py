import pytest
from unittest.mock import Mock, patch
from app.payments.daraja_client import DarajaClient
from app.payments.payment_processor import PaymentProcessor

class TestDarajaClient:
    """Test Daraja API client functionality"""
    
    @pytest.fixture
    def daraja_client(self):
        """Create Daraja client with test credentials"""
        with patch.dict('os.environ', {
            'DARAJA_CONSUMER_KEY': 'test_key',
            'DARAJA_CONSUMER_SECRET': 'test_secret',
            'DARAJA_BUSINESS_SHORT_CODE': '123456',
            'DARAJA_PASSKEY': 'test_passkey'
        }):
            return DarajaClient()
    
    def test_format_phone_number(self, daraja_client):
        """Test phone number formatting"""
        # Test various input formats
        assert daraja_client._format_phone_number("0712345678") == "254712345678"
        assert daraja_client._format_phone_number("254712345678") == "254712345678"
        assert daraja_client._format_phone_number("712345678") == "254712345678"
        assert daraja_client._format_phone_number("+254712345678") == "254712345678"
    
    @patch('app.payments.daraja_client.requests.get')
    def test_get_access_token_success(self, mock_get, daraja_client):
        """Test successful access token retrieval"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token"}
        mock_get.return_value = mock_response
        
        token = daraja_client._get_access_token()
        assert token == "test_token"
        mock_get.assert_called_once()
    
    @patch('app.payments.daraja_client.requests.post')
    @patch.object(DarajaClient, '_get_access_token')
    def test_initiate_stk_push_success(self, mock_get_token, mock_post, daraja_client):
        """Test successful STK push initiation"""
        # Mock access token
        mock_get_token.return_value = "test_token"
        
        # Mock successful STK response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "MerchantRequestID": "test_merchant_id",
            "CheckoutRequestID": "test_checkout_id",
            "ResponseCode": "0",
            "ResponseDescription": "Success",
            "CustomerMessage": "Request sent to your phone"
        }
        mock_post.return_value = mock_response
        
        result = daraja_client.initiate_stk_push(
            phone_number="254712345678",
            amount=100.0,
            account_reference="TEST123",
            transaction_desc="Test payment"
        )
        
        assert result["success"] == True
        assert result["merchant_request_id"] == "test_merchant_id"
        assert result["checkout_request_id"] == "test_checkout_id"

class TestPaymentProcessor:
    """Test payment processor functionality"""
    
    @pytest.fixture
    def payment_processor(self):
        """Create payment processor with mocked dependencies"""
        with patch('app.payments.payment_processor.daraja_client'):
            return PaymentProcessor()
    
    def test_process_successful_payment(self, payment_processor):
        """Test processing of successful payment"""
        # This would test the internal payment processing logic
        # Implementation depends on your specific business logic
        pass
    
    def test_get_user_payment_history(self, payment_processor):
        """Test retrieving user payment history"""
        # Add some test payments
        payment_processor.pending_payments = {
            "test_payment_1": {
                "user_id": "user123",
                "amount": 100.0,
                "status": "completed",
                "product_info": {"name": "Test Product"},
                "created_at": "2024-01-01T00:00:00"
            }
        }
        
        history = payment_processor.get_user_payment_history("user123")
        assert len(history) == 1
        assert history[0]["amount"] == 100.0

if __name__ == "__main__":
    pytest.main([__file__])