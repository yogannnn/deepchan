import hashlib
import secrets

import pytest
from flask import g, request


def test_i2p_same_dest_gets_same_id(app):
    """Одинаковый X-I2P-DestB32 → одинаковый идентификатор."""
    with app.test_request_context(headers={"X-I2P-DestB32": "dest123"}):
        app.preprocess_request()
        id1 = g.identity["id"]
        transport1 = g.identity["transport"]
    with app.test_request_context(headers={"X-I2P-DestB32": "dest123"}):
        app.preprocess_request()
        id2 = g.identity["id"]
        transport2 = g.identity["transport"]
    assert id1 == id2
    assert transport1 == transport2 == "i2p"


def test_i2p_different_dest_gets_different_id(app):
    """Разные X-I2P-DestB32 → разные идентификаторы."""
    with app.test_request_context(headers={"X-I2P-DestB32": "destA"}):
        app.preprocess_request()
        idA = g.identity["id"]
    with app.test_request_context(headers={"X-I2P-DestB32": "destB"}):
        app.preprocess_request()
        idB = g.identity["id"]
    assert idA != idB


def test_i2p_desthash_fallback(app):
    """Если нет DestB32, используется X-I2P-DestHash."""
    with app.test_request_context(headers={"X-I2P-DestHash": "desthash1"}):
        app.preprocess_request()
        id1 = g.identity["id"]
        transport1 = g.identity["transport"]
    with app.test_request_context(headers={"X-I2P-DestHash": "desthash1"}):
        app.preprocess_request()
        id2 = g.identity["id"]
        transport2 = g.identity["transport"]
    assert id1 == id2
    assert transport1 == transport2 == "i2p"


def test_i2p_no_headers_uses_clearnet(app):
    """Нет I2P-заголовков → клирнет."""
    with app.test_request_context(environ_base={"REMOTE_ADDR": "1.2.3.4"}):
        app.preprocess_request()
        assert g.identity["transport"] == "clearnet"


def test_tor_generates_new_session(app):
    """Onion-хост без куки → новый sesid, устанавливается кука."""
    with app.test_request_context(headers={"Host": "example.onion"}):
        app.preprocess_request()
        assert g.identity["transport"] == "tor"
        assert "id" in g.identity
        # after_request добавит куку
        rv = app.full_dispatch_request()
        assert "Set-Cookie" in rv.headers
        cookie = rv.headers["Set-Cookie"]
        assert "deepchan_tor_id=" in cookie
        assert g.identity["id"] in cookie


def test_tor_keeps_session(app):
    """Tor повторно заходит с кукой → id сохраняется."""
    sesid = secrets.token_hex(16)
    with app.test_request_context(
        headers={"Host": "example.onion", "Cookie": f"deepchan_tor_id={sesid}"}
    ):
        app.preprocess_request()
        assert g.identity["transport"] == "tor"
        assert g.identity["id"] == sesid


def test_tor_uses_any_cookie_value(app):
    """Tor с кукой любого значения использует это значение как id."""
    with app.test_request_context(
        headers={"Host": "example.onion", "Cookie": "deepchan_tor_id=invalid"}
    ):
        app.preprocess_request()
        assert g.identity["transport"] == "tor"
        assert g.identity["id"] == "invalid"


def test_tor_missing_cookie_generates_new(app):
    """Tor без куки генерирует новый id."""
    with app.test_request_context(headers={"Host": "example.onion"}):
        app.preprocess_request()
        assert g.identity["transport"] == "tor"
        first_id = g.identity["id"]
    # второй запрос без куки – другой id
    with app.test_request_context(headers={"Host": "example.onion"}):
        app.preprocess_request()
        second_id = g.identity["id"]
        assert first_id != second_id


def test_clearnet_ip_hash_stable(app):
    """Один и тот же IP даёт одинаковый identity."""
    with app.test_request_context(environ_base={"REMOTE_ADDR": "1.2.3.4"}):
        app.preprocess_request()
        id1 = g.identity["id"]
    with app.test_request_context(environ_base={"REMOTE_ADDR": "1.2.3.4"}):
        app.preprocess_request()
        id2 = g.identity["id"]
    assert id1 == id2


def test_clearnet_secret_key_affects_hash(app):
    """Смена SECRET_KEY меняет хеш IP."""
    with app.test_request_context(environ_base={"REMOTE_ADDR": "5.6.7.8"}):
        app.preprocess_request()
        id1 = g.identity["id"]
    app.config["SECRET_KEY"] = "different-secret"
    with app.test_request_context(environ_base={"REMOTE_ADDR": "5.6.7.8"}):
        app.preprocess_request()
        id2 = g.identity["id"]
    assert id1 != id2
