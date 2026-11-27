# Isolated pytest runner for rewritten PR code.
# Build: docker build -t autonomous-code-review-sandbox ./backend/sandbox
FROM python:3.12-slim

RUN pip install --no-cache-dir pytest>=8.0.0 \
    && useradd --create-home --uid 10001 sandbox

WORKDIR /work
USER sandbox

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    PYTHONPYCACHEPREFIX=/tmp/pycache

ENTRYPOINT ["python", "-m", "pytest"]
CMD ["test_solution.py", "-q", "--tb=line", "-p", "no:cacheprovider"]
