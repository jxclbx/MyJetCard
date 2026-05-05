import time


class ApiTimingMiddleware:
    """
    为所有 /api/ 开头的请求在响应头中注入 X-Process-Time (ms)，
    记录后端从收到请求到返回响应的处理耗时。
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            start = time.perf_counter()
            response = self.get_response(request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            response["X-Process-Time"] = f"{elapsed_ms:.1f}"
            response["Access-Control-Expose-Headers"] = "X-Process-Time"
            return response
        return self.get_response(request)
