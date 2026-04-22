import pytest
from src.dashboard.auth import User, filter_sellers_by_role

def test_user_creation():
    user = User("1", "testuser", "pass", "SELLER", seller_id=10, is_active=True)
    assert user.id == "1"
    assert user.username == "testuser"
    assert user.password == "pass"
    assert user.role == "SELLER"
    assert user.seller_id == 10
    assert user.managed_sellers == []
    assert user.is_active is True

def test_user_creation_with_managed():
    user = User("2", "manager", "pass", "MANAGER", managed_sellers=[1, 2, 3])
    assert user.managed_sellers == [1, 2, 3]

def test_filter_sellers_by_role_admin():
    admin = User("1", "admin", "pass", "ADMIN")
    all_sellers = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    # Admin should see all
    assert filter_sellers_by_role(admin, all_sellers) == all_sellers

def test_filter_sellers_by_role_manager():
    manager = User("2", "manager", "pass", "MANAGER", managed_sellers=[1])
    all_sellers = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    # Manager should only see managed
    assert filter_sellers_by_role(manager, all_sellers) == [{"id": 1, "name": "A"}]

def test_filter_sellers_by_role_seller():
    seller = User("3", "seller", "pass", "SELLER", seller_id=2)
    all_sellers = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    # Seller should only see themselves
    assert filter_sellers_by_role(seller, all_sellers) == [{"id": 2, "name": "B"}]
