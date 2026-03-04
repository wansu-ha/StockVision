from fastapi import APIRouter, HTTPException
from kiwoom.session import get_session
from kiwoom.account import KiwoomAccount

router = APIRouter(prefix="/api/kiwoom", tags=["kiwoom"])

_account = KiwoomAccount()


@router.get("/status")
def kiwoom_status():
    return {"success": True, "data": get_session().status()}


@router.get("/account")
def kiwoom_account():
    session = get_session()
    if not session.connected:
        raise HTTPException(status_code=503, detail="키움 미연결")
    accounts = _account.get_account_list()
    if not accounts:
        raise HTTPException(status_code=503, detail="계좌 없음")
    account_no = accounts[0]
    balance   = _account.get_balance(account_no)
    positions = _account.get_positions(account_no)
    return {"success": True, "data": {"balance": balance, "positions": positions}}
