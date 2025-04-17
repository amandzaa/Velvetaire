from datetime import datetime
import re
from flask import Blueprint, request, jsonify
from app.services.account import AccountService
from app.utils import helpers
from app.utils.auth import admin_required, token_required
from app.utils.database_session_manager import get_db_session
from app.services.transaction import TransactionService

transaction_bp = Blueprint('transaction_bp', __name__, url_prefix='/revoubank/transactions')

@transaction_bp.route('/all', methods=['GET'])
@token_required
@admin_required
def get_all_transactions_all_users():
    db_session = get_db_session()
    transaction_service = TransactionService(db_session)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    try:
        start_date = None
        end_date = None
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str)
        # Get all transactions
        transactions = transaction_service.get_all_transactions_admin(
            start_date=start_date,
            end_date=end_date
        )
        return jsonify(transactions)
    except ValueError as e:
        return jsonify({'message': f"Invalid date format: {str(e)}"}), 400
    except Exception as e:
        return jsonify({'message': str(e)}), 500
    finally:
        db_session.close()

@transaction_bp.route('/userid/<string:user_id>', methods=['GET'])
@token_required
def get_all_transactions_by_account_id(user_id):
    authorized, error_message, status_code = helpers.check_user_owner(user_id)
    if not authorized:
        return error_message, status_code
    db_session = get_db_session()
    transaction_service = TransactionService(db_session)
    account_id = request.args.get('account_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    try:
        transactions = transaction_service.get_user_transactions(
            user_id=user_id,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date
        )
        return jsonify([transaction.to_dict() for transaction in transactions])
    except Exception as e:
        return jsonify({'message': str(e)}), 500
    finally:
        db_session.close()

@transaction_bp.route('/create', methods=['POST'])
@token_required
def create_transaction():
    db_session = get_db_session()
    transaction_service = TransactionService(db_session)
    data = request.json
    try:
        success, result, status_code = transaction_service.create_transaction(data)
        if success:
            db_session.commit()
        else:
            db_session.rollback()
        if not success:
            return jsonify({'message': str(result)}), status_code
        # Make sure result is JSON serializable
        if isinstance(result, dict):
            # If a transaction object is in the result, ensure it's serializable
            if 'transaction' in result and hasattr(result['transaction'], 'to_dict'):
                result['transaction'] = result['transaction'].to_dict()
        return jsonify(result), status_code
    except Exception as e:
        db_session.rollback()
        return jsonify({'message': str(e)}), 500
    finally:
        db_session.close()

@transaction_bp.route('/<string:identifier>/info', methods=['GET'])
@token_required
def get_transaction_info_by_identifier(identifier):
    is_transaction_number = helpers.is_valid_transaction_number(identifier)
    db_session = get_db_session()
    transaction_service = TransactionService(db_session)
    auth, error_response, status_code = transaction_service.check_transaction_auth_by_identifier(
        identifier, is_transaction_number=is_transaction_number)
    if not auth:
        return error_response, status_code
    try:
        success, response_data, status_code = transaction_service.get_transaction_by_identifier(
            identifier, is_transaction_number=is_transaction_number)
        if not success:
            return jsonify({'message': response_data}), status_code
        return jsonify(response_data), status_code
    except Exception as e:
        return jsonify({'message': str(e)}), 500
    finally:
        db_session.close()
        

@transaction_bp.route('/account/<string:account_identifier>', methods=['GET'])
@token_required
def get_transactions_by_account_identifier(account_identifier):
    db_session = get_db_session()
    transaction_service = TransactionService(db_session)
    
    is_account_number = bool(re.fullmatch(r"ACC-\d+-\d+", account_identifier))
    is_owner, error_response, status_code = helpers.check_account_owner_by_identifier(
        account_identifier, is_account_number=is_account_number)
    if not is_owner:
        return error_response, status_code
    # Parse query parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    try:
        # Get transactions
        transactions = transaction_service.get_transactions_by_account_identifier(
            identifier=account_identifier,
            is_account_number=is_account_number,
            start_date=start_date_str,
            end_date=end_date_str
        )
        
        return jsonify([transaction.to_dict() for transaction in transactions])
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': str(e)}), 500
    finally:
        db_session.close()