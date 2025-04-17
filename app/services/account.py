from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional
from flask import g, request, jsonify
from sqlalchemy.orm import Session

from app.repositories.account import AccountRepository
from app.utils.database_session_manager import get_db_session

class AccountService:
    def __init__(self, session: Optional[Session] = None):
        self.db_session = session or get_db_session()
        self.repository = AccountRepository(self.db_session)
    
    def create_account(self, user_id: str, account_name: str, account_type: str, 
                    account_number: str, currency: str, initial_balance: float = 0) -> Tuple[bool, str, Optional[str]]:
        valid_types = ['checking', 'savings', 'investment','deposit']
        if account_type not in valid_types:
            return False, f"Invalid account type. Must be one of: {', '.join(valid_types)}", None
        return self.repository.create(
            user_id, 
            account_name,
            account_type,
            account_number,
            currency, 
            initial_balance
        )
    
    def get_user_accounts(self, user_id: str) -> List[Any]:
        # Convert user_id to integer if passed as string
        user_id_int = int(user_id) if isinstance(user_id, str) else user_id
        return self.repository.find_by_user_id(user_id_int)
    
    def get_all_accounts(self) -> List[Any]:
        return self.repository.find_all_accounts()
    
    def get_account_by_identifier(self, identifier: str, is_account_number: bool = False) -> Optional[Any]:
        """Get account by either account_id or account_number"""
        if is_account_number:
            return self.repository.find_by_account_number(identifier)
        else:
            return self.repository.find_by_id(identifier)
            
    def get_account_info_by_identifier(self, identifier: str, is_account_number: bool = False) -> Tuple[bool, Dict[str, Any], int]:
        """Get account info by either account_id or account_number"""
        if is_account_number:
            account = self.repository.find_by_account_number(identifier)
            if not account:
                return False, {'message': 'Account not found!'}, 404
            return True, account.to_dict(), 200
        else:
            return self.get_account_info(identifier)
            
    def delete_account_by_identifier(self, identifier: str, is_account_number: bool = False) -> Tuple[bool, Any, int]:
        """Delete account by either account_id or account_number"""
        account = self.get_account_by_identifier(identifier, is_account_number)
        if not account:
            return False, jsonify({'message': 'Account not found!'}), 404
        if account.balance > 0:
            return False, jsonify({'message': 'Cannot delete account with positive balance!'}), 400
        account_id = account.id
        success, message = self.repository.delete(account_id)
        if not success:
            return False, jsonify({'message': message}), 500
        return True, jsonify({'message': 'Account deleted successfully'}), 200
        
    def update_account_info_by_identifier(self, identifier: str, is_account_number: bool = False) -> Dict[str, str]:
        """Update account by either account_id or account_number"""
        account = self.get_account_by_identifier(identifier, is_account_number)
        if not account:
            raise ValueError('Account not found!')
        data = request.json
        if not data:
            raise ValueError('No data provided!')
        updates = {}
        allowed_fields = ['account_name', 'account_type', 'currency', 'status']
        for field in allowed_fields:
            if field in data and data[field]:
                updates[field] = data[field]
        if not updates:
            raise ValueError('No valid fields to update!')
        # Add updated_at timestamp
        updates['updated_at'] = datetime.now()
        return self.repository.update_account(account.id, updates)