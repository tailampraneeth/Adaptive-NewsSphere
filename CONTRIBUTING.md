# Contributing to Adaptive NewsSphere

Thank you for your interest in contributing to Adaptive NewsSphere! We welcome all contributions, including bug reports, feature requests, documentation improvements, and code changes.

## Development Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/Adaptive-NewsSphere.git
    cd Adaptive-NewsSphere
    ```

2.  **Environment Setup:**
    Create a local Python virtual environment (Python 3.13 recommended) and install dependencies:
    ```bash
    python -m venv .venv
    .\.venv\Scripts\activate
    pip install -r backend/requirements.txt
    ```

3.  **Start Local Infrastructure:**
    Ensure Docker Desktop is running, then start database and cache containers:
    ```powershell
    docker compose up -d
    ```

4.  **Run Database Migrations:**
    ```bash
    cd backend
    python -m alembic upgrade head
    ```

## Development Guidelines

*   **Code Style:** Follow standard PEP 8 formatting. Run `ruff check .` to lint code.
*   **Static Typing:** Run `mypy .` to verify type safety.
*   **Testing:** Add unit tests under `backend/tests/` and verify they pass using:
    ```bash
    pytest
    ```

## Submission Process

1.  Create a branch for your edits: `git checkout -b feature/amazing-feature`
2.  Commit your changes following meaningful commit messages.
3.  Push your branch: `git push origin feature/amazing-feature`
4.  Open a Pull Request (PR) describing the changes and linking to related issues.
