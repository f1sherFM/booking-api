def test_request_id_header_is_present(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


def test_metrics_endpoint_returns_prometheus_text(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    body = response.text
    assert "http_requests_total" in body
    assert "http_request_duration_seconds" in body
