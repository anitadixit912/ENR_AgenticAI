"""Unit tests for send_alert_email tool (BTP ANS OAuth + SMTP fallback)."""
import os
from unittest.mock import patch, MagicMock

SAMPLE_SUPPLIERS = [{"supplier_id": "SUP001", "name": "ACME Corp", "country": "UA"}]

ANS_ENV = {
    "BTP_ANS_URL":           "https://ans.cfapps.eu10.hana.ondemand.com",
    "BTP_ANS_TOKEN_URL":     "https://my-subaccount.authentication.eu10.hana.ondemand.com/oauth/token",
    "BTP_ANS_CLIENT_ID":     "sb-test-client",
    "BTP_ANS_CLIENT_SECRET": "test-secret",
}


# ââ Helpers ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def _mock_urlopen_sequence(*responses):
    """Return a side_effect list so urlopen returns different mocks per call."""
    mocks = []
    for resp_data, status in responses:
        m = MagicMock()
        m.status = status
        m.read.return_value = resp_data if isinstance(resp_data, bytes) else resp_data.encode()
        m.__enter__ = lambda s: s
        m.__exit__ = MagicMock(return_value=False)
        mocks.append(m)
    return mocks


# ââ Severity / recipient guard tests âââââââââââââââââââââââââââââââââââââââââ

def test_send_email_skipped_low_severity():
    from tools.alert_tool import send_alert_email
    result = send_alert_email.invoke({
        "recipients": ["buyer@company.com"],
        "event_title": "Minor protest",
        "severity": "Low",
        "affected_suppliers": SAMPLE_SUPPLIERS,
        "affected_po_count": 2,
        "total_po_value": 5000.0,
        "dashboard_url": "http://localhost:4004",
    })
    assert result["sent"] is False


def test_send_email_skipped_medium_severity():
    from tools.alert_tool import send_alert_email
    result = send_alert_email.invoke({
        "recipients": ["buyer@company.com"],
        "event_title": "Trade disruption",
        "severity": "Medium",
        "affected_suppliers": SAMPLE_SUPPLIERS,
        "affected_po_count": 1,
        "total_po_value": 10000.0,
        "dashboard_url": "http://localhost:4004",
    })
    assert result["sent"] is False


def test_send_email_no_recipients():
    from tools.alert_tool import send_alert_email
    result = send_alert_email.invoke({
        "recipients": [],
        "event_title": "Military conflict",
        "severity": "High",
        "affected_suppliers": SAMPLE_SUPPLIERS,
        "affected_po_count": 5,
        "total_po_value": 100000.0,
        "dashboard_url": "http://localhost:4004",
    })
    assert result["sent"] is False


# ââ BTP ANS (Option A) tests ââââââââââââââââââââââââââââââââââââââââââââââââââ

def test_send_email_via_btp_ans_critical():
    """BTP ANS happy path for Critical severity â OAuth token fetch + event POST."""
    token_resp  = b'{"access_token": "mock-token-abc", "token_type": "bearer"}'
    event_resp  = b'{"id": "ans-event-001"}'
    side_effects = _mock_urlopen_sequence((token_resp, 200), (event_resp, 202))

    with patch.dict(os.environ, ANS_ENV, clear=True):
        with patch("urllib.request.urlopen", side_effect=side_effects):
            from tools.alert_tool import send_alert_email
            result = send_alert_email.invoke({
                "recipients": ["anita.dixit@sap.com"],
                "event_title": "Military offensive escalates in eastern Ukraine",
                "severity": "Critical",
                "affected_suppliers": SAMPLE_SUPPLIERS,
                "affected_po_count": 10,
                "total_po_value": 500000.0,
                "dashboard_url": "http://localhost:4004",
            })

    assert result["sent"] is True
    assert result["recipient_count"] == 1
    assert result["message_id"] == "ans-event-001"


def test_send_email_via_btp_ans_high():
    """BTP ANS happy path for High severity."""
    token_resp = b'{"access_token": "mock-token-xyz"}'
    event_resp = b'{"id": "ans-event-002"}'
    side_effects = _mock_urlopen_sequence((token_resp, 200), (event_resp, 202))

    with patch.dict(os.environ, ANS_ENV, clear=True):
        with patch("urllib.request.urlopen", side_effect=side_effects):
            from tools.alert_tool import send_alert_email
            result = send_alert_email.invoke({
                "recipients": ["anita.dixit@sap.com", "cpo@company.com"],
                "event_title": "Sanctions expanded on Russian steel sector",
                "severity": "High",
                "affected_suppliers": SAMPLE_SUPPLIERS,
                "affected_po_count": 3,
                "total_po_value": 287500.0,
                "dashboard_url": "http://localhost:4004",
            })

    assert result["sent"] is True
    assert result["recipient_count"] == 2


def test_send_email_btp_ans_oauth_fails_then_smtp_fallback():
    """ANS OAuth token fetch fails â falls back to SMTP."""
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: s
    mock_smtp.__exit__ = MagicMock(return_value=False)

    env = {**ANS_ENV, "SMTP_HOST": "smtp.example.com", "SMTP_PORT": "587",
           "SMTP_USER": "sender@sap.com", "SMTP_PASS": "secret"}

    with patch.dict(os.environ, env, clear=True):
        with patch("urllib.request.urlopen", side_effect=Exception("ANS token endpoint unreachable")):
            with patch("smtplib.SMTP", return_value=mock_smtp):
                from tools.alert_tool import send_alert_email
                result = send_alert_email.invoke({
                    "recipients": ["anita.dixit@sap.com"],
                    "event_title": "Active conflict near supplier facilities",
                    "severity": "Critical",
                    "affected_suppliers": SAMPLE_SUPPLIERS,
                    "affected_po_count": 8,
                    "total_po_value": 750000.0,
                    "dashboard_url": "http://localhost:4004",
                })

    assert result["sent"] is True
    assert result["message_id"] is not None


def test_send_email_btp_ans_event_post_fails_then_smtp_fallback():
    """ANS token succeeds but event POST fails â falls back to SMTP."""
    token_resp = b'{"access_token": "mock-token"}'
    token_mock = MagicMock()
    token_mock.status = 200
    token_mock.read.return_value = token_resp
    token_mock.__enter__ = lambda s: s
    token_mock.__exit__ = MagicMock(return_value=False)

    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: s
    mock_smtp.__exit__ = MagicMock(return_value=False)

    def urlopen_side_effect(req, timeout=10):
        if "oauth/token" in req.full_url:
            return token_mock
        raise Exception("ANS event endpoint 503")

    env = {**ANS_ENV, "SMTP_HOST": "smtp.example.com"}

    with patch.dict(os.environ, env, clear=True):
        with patch("urllib.request.urlopen", side_effect=urlopen_side_effect):
            with patch("smtplib.SMTP", return_value=mock_smtp):
                from tools.alert_tool import send_alert_email
                result = send_alert_email.invoke({
                    "recipients": ["anita.dixit@sap.com"],
                    "event_title": "Port disruptions in Nigeria",
                    "severity": "High",
                    "affected_suppliers": SAMPLE_SUPPLIERS,
                    "affected_po_count": 2,
                    "total_po_value": 156000.0,
                    "dashboard_url": "http://localhost:4004",
                })

    assert result["sent"] is True


# ââ SMTP-only tests âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def test_send_email_via_smtp_only():
    """SMTP path when no ANS credentials are set."""
    env = {"SMTP_HOST": "smtp.example.com", "SMTP_PORT": "587",
           "SMTP_USER": "user@example.com", "SMTP_PASS": "secret"}

    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: s
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch.dict(os.environ, env, clear=True):
        with patch("smtplib.SMTP", return_value=mock_smtp):
            from tools.alert_tool import send_alert_email
            result = send_alert_email.invoke({
                "recipients": ["buyer@company.com"],
                "event_title": "Conflict in Eastern Europe",
                "severity": "High",
                "affected_suppliers": SAMPLE_SUPPLIERS,
                "affected_po_count": 4,
                "total_po_value": 200000.0,
                "dashboard_url": "http://localhost:4004",
            })

    assert result["sent"] is True
    assert result["recipient_count"] == 1
    assert result["message_id"] is not None


# ââ No service configured âââââââââââââââââââââââââââââââââââââââââââââââââââââ

def test_send_email_no_service_configured():
    """Returns sent=False when neither ANS nor SMTP is configured."""
    with patch.dict(os.environ, {}, clear=True):
        from tools.alert_tool import send_alert_email
        result = send_alert_email.invoke({
            "recipients": ["buyer@company.com"],
            "event_title": "High risk event",
            "severity": "High",
            "affected_suppliers": SAMPLE_SUPPLIERS,
            "affected_po_count": 3,
            "total_po_value": 75000.0,
            "dashboard_url": "http://localhost:4004",
        })
    assert result["sent"] is False
    assert "No alert service" in result.get("reason", "")


# ââ Recommendations in email body tests âââââââââââââââââââââââââââââââââââââââ

SAMPLE_RECS = [
    "IMMEDIATE: Activate emergency procurement protocol â contact all affected suppliers within 24 hours.",
    "Initiate alternative sourcing from pre-approved backup suppliers outside the conflict zone.",
    "Expedite open POs with delivery dates within the next 30 days â request early shipment.",
]


def test_send_email_includes_recommendations_block_for_critical():
    """Critical severity + recommendations â email body contains AI recommendations section."""
    import json as _json
    token_resp = b'{"access_token": "mock-token-recs"}'
    event_resp = b'{"id": "ans-recs-001"}'
    side_effects = _mock_urlopen_sequence((token_resp, 200), (event_resp, 202))
    ans_event_bodies = []

    def capture_and_return(req, timeout=10):
        try:
            raw = req.data.decode()
            if raw.startswith("{"):
                parsed = _json.loads(raw)
                ans_event_bodies.append(parsed.get("body", ""))
        except Exception:
            pass
        return side_effects.pop(0)

    with patch.dict(os.environ, ANS_ENV, clear=True):
        with patch("urllib.request.urlopen", side_effect=capture_and_return):
            from tools.alert_tool import send_alert_email
            result = send_alert_email.invoke({
                "recipients": ["buyer@company.com"],
                "event_title": "Military offensive in eastern Ukraine",
                "severity": "Critical",
                "affected_suppliers": SAMPLE_SUPPLIERS,
                "affected_po_count": 8,
                "total_po_value": 450000.0,
                "dashboard_url": "http://localhost:4004",
                "recommendations": SAMPLE_RECS,
            })

    assert result["sent"] is True
    assert len(ans_event_bodies) == 1, "Expected exactly one ANS event POST"
    email_body = ans_event_bodies[0]
    assert "MITIGATION RECOMMENDATIONS" in email_body
    assert "emergency procurement" in email_body.lower()


def test_send_email_via_smtp_includes_recommendations():
    """SMTP path: decoded email body should contain the recommendations section."""
    import base64, quopri, email as _email
    captured_msg = []
    mock_smtp_instance = MagicMock()
    mock_smtp_instance.__enter__ = lambda s: s
    mock_smtp_instance.__exit__ = MagicMock(return_value=False)

    def capture_sendmail(from_addr, to_addrs, msg_str):
        captured_msg.append(msg_str)

    mock_smtp_instance.sendmail = capture_sendmail

    env = {"SMTP_HOST": "smtp.example.com", "SMTP_PORT": "587",
           "SMTP_USER": "user@example.com", "SMTP_PASS": "secret"}

    with patch.dict(os.environ, env, clear=True):
        with patch("smtplib.SMTP", return_value=mock_smtp_instance):
            from tools.alert_tool import send_alert_email
            result = send_alert_email.invoke({
                "recipients": ["buyer@company.com"],
                "event_title": "Sanctions expanded on Russian steel sector",
                "severity": "High",
                "affected_suppliers": SAMPLE_SUPPLIERS,
                "affected_po_count": 3,
                "total_po_value": 180000.0,
                "dashboard_url": "http://localhost:4004",
                "recommendations": SAMPLE_RECS,
            })

    assert result["sent"] is True
    # Parse and decode the MIME message to get the plain-text body
    raw_msg = " ".join(captured_msg)
    msg_obj = _email.message_from_string(raw_msg)
    payload = msg_obj.get_payload(decode=True)
    if payload:
        decoded_body = payload.decode("utf-8", errors="replace")
    else:
        decoded_body = raw_msg  # fallback if not encoded
    assert "MITIGATION RECOMMENDATIONS" in decoded_body
    assert "emergency procurement" in decoded_body.lower()


def test_send_email_no_recommendations_section_when_empty():
    """Email body must NOT contain the recommendations section when list is empty."""
    captured_msg = []
    mock_smtp_instance = MagicMock()
    mock_smtp_instance.__enter__ = lambda s: s
    mock_smtp_instance.__exit__ = MagicMock(return_value=False)

    def capture_sendmail(from_addr, to_addrs, msg_str):
        captured_msg.append(msg_str)

    mock_smtp_instance.sendmail = capture_sendmail

    env = {"SMTP_HOST": "smtp.example.com"}
    with patch.dict(os.environ, env, clear=True):
        with patch("smtplib.SMTP", return_value=mock_smtp_instance):
            from tools.alert_tool import send_alert_email
            result = send_alert_email.invoke({
                "recipients": ["buyer@company.com"],
                "event_title": "Supply chain disruption",
                "severity": "High",
                "affected_suppliers": SAMPLE_SUPPLIERS,
                "affected_po_count": 2,
                "total_po_value": 95000.0,
                "dashboard_url": "http://localhost:4004",
                "recommendations": [],
            })

    assert result["sent"] is True
    full_msg = " ".join(captured_msg)
    assert "MITIGATION RECOMMENDATIONS" not in full_msg


def test_send_email_low_severity_not_sent_even_with_recommendations():
    """Low severity: email must not be sent even if recommendations are provided."""
    from tools.alert_tool import send_alert_email
    result = send_alert_email.invoke({
        "recipients": ["buyer@company.com"],
        "event_title": "Minor political tension",
        "severity": "Low",
        "affected_suppliers": SAMPLE_SUPPLIERS,
        "affected_po_count": 1,
        "total_po_value": 2000.0,
        "dashboard_url": "http://localhost:4004",
        "recommendations": SAMPLE_RECS,
    })
    assert result["sent"] is False
