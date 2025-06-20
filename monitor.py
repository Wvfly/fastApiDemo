from prometheus_client import Counter, Histogram
from fastapi import Request

REQUEST_COUNT = Counter(
    'fastapi_requests_total',
    'Total count of requests',
    ['method', 'path', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'fastapi_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'path']
)

def monitor_request(request: Request, response):
    path = request.url.path
    REQUEST_COUNT.labels(
        method=request.method,
        path=path,
        status_code=response.status_code
    ).inc()