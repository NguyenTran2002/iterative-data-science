# One image for both sides of a pair and for the task writer.
# Two separate environments, so an agent's `pip install` can never touch the runner:
#   /opt/runner/.venv  the Agent SDK (which bundles Claude Code) and the runner
#   /opt/venv          the data-science stack, owned by the agent's user, first on its PATH
FROM python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb

COPY --from=ghcr.io/astral-sh/uv:0.11.29@sha256:eb2843a1e56fd9e30c7276ce1a52cba86e64c7b385f5e3279a0e08e02dd058fc /uv /uvx /bin/
ENV UV_NO_CACHE=1 UV_LINK_MODE=copy

RUN useradd -m analyst

COPY requirements/ /tmp/requirements/
RUN uv venv /opt/runner/.venv \
 && uv pip install --python /opt/runner/.venv/bin/python -r /tmp/requirements/runner.txt
RUN uv venv --seed /opt/venv \
 && uv pip install --python /opt/venv/bin/python -r /tmp/requirements/analysis.txt \
 && chown -R analyst:analyst /opt/venv \
 && rm -rf /tmp/requirements

COPY runner/ /opt/runner/runner/

ENV DISABLE_AUTOUPDATER=1
USER analyst
WORKDIR /opt/runner
ENTRYPOINT ["/opt/runner/.venv/bin/python", "-m", "runner.run"]
