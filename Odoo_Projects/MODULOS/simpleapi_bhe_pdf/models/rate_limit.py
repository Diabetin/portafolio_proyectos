# -*- coding: utf-8 -*-
import time, random, threading
import requests

class SimpleAPIRateLimiter:
    """
    Limitador de tasa para llamadas HTTP:
    - Asegura intervalo mínimo entre solicitudes (min_interval).
    - Respeta Retry-After en 429 cuando está presente.
    - Reintenta con backoff exponencial y jitter para fallos transitorios.
    """
    def __init__(self, min_interval_sec=1.0, max_retries=5, base_delay=1.0, factor=2.0, max_delay=30.0):
        self.min_interval = float(min_interval_sec)
        self.lock = threading.Lock()
        self.last_call_ts = 0.0
        self.max_retries = int(max_retries)
        self.base_delay = float(base_delay)
        self.factor = float(factor)
        self.max_delay = float(max_delay)

    def _sleep_until_slot(self):
        with self.lock:
            now = time.time()
            wait = self.min_interval - (now - self.last_call_ts)
            if wait > 0:
                time.sleep(wait)
            self.last_call_ts = time.time()

    def _get_retry_after(self, resp):
        ra = resp.headers.get('Retry-After')
        if not ra:
            return None
        try:
            return float(ra)
        except Exception:
            return None

    def request(self, method, url, session=None, respect_slot=True, **kwargs):
        sess = session or requests
        attempt = 0
        last_exc = None
        while attempt <= self.max_retries:
            if respect_slot:
                self._sleep_until_slot()
            try:
                resp = sess.request(method, url, **kwargs)
            except Exception as e:
                last_exc = e
                delay = min(self.base_delay * (self.factor ** attempt), self.max_delay)
                delay *= random.uniform(0.5, 1.5)
                time.sleep(delay)
                attempt += 1
                continue

            if resp.status_code == 429:
                ra = self._get_retry_after(resp)
                if ra is not None:
                    time.sleep(max(0.0, ra))
                else:
                    delay = min(self.base_delay * (self.factor ** attempt), self.max_delay)
                    delay *= random.uniform(0.5, 1.5)
                    time.sleep(delay)
                attempt += 1
                continue

            return resp

        if last_exc:
            raise last_exc
        raise requests.HTTPError("Max retries exceeded")
#hola