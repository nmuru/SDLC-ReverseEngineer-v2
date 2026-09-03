# Software Requirements

This section reconstructs the requirements that the repository reveals the system was designed to satisfy. Requirements were derived from concrete artifacts in the repository—configuration, source code, templates, data files, and documentation—rather than from generic best-practice or technology assumptions.

## Certainty Classifications

Each requirement is labeled to indicate the confidence of its derivation:

| Classification | Meaning |
|----------------|---------|
| **Verified** | Directly stated or strongly established by executable behavior and supporting artifacts |
| **Inferred** | Not explicitly stated, but necessary or strongly implied by multiple implementation artifacts |
| **Uncertain** | Plausible interpretation with insufficient evidence to establish confidence |

Evidence is cited inline using repository-relative paths.

---

## 2. Functional Requirements

### 2.1 Source Acquisition

**R-F-1 — Accept a remote git source URL as primary input**  
*Verified.*  
Evidence: `index.html` exposes a form field bound to a `repo` variable (`<input name="repo" ...>`) and routes submit the value through the controller. `application.py` routes `/<repo_owner>/<repo_name>` and the `index` route render the form with a placeholder of the form `https://github.com/<owner>/<repo>`.

**R-F-2 — Accept optional local-path input as an alternative source**  
*Verified.*  
Evidence: `index.html` declares `<input name="local" ...>` and the controller reads `request.values.get('local')` in `application.py`.

**R-F-3 — Acquire the requested git repository into a local working directory**  
*Verified.*  
Evidence: `application.py` constructs `Repo.clone_from(repo, dir_path)` and falls back to `Repo(dir_path)` when a local input is supplied.

**R-F-4 — Treat absence of either remote URL or local path as a rejected request**  
*Inferred.*  
Evidence: The code path proceeds only when `repo` is populated or a local path is given; the system relies on at least one of the two inputs to construct a `Repo` instance.

### 2.2 Source Inspection

**R-F-5 — Walk the repository tree to identify Python source files**  
*Verified.*  
Evidence: `get_python_files()` recursively traverses `repo.head.commit.tree` selecting files ending in `.py`.

**R-F-6 — Read the textual content of each Python file**  
*Verified.*  
Evidence: `get_python_content()` reads bytes per file via `Blob.data_stream.read()` and decodes with `errors='replace'`.

**R-F-7 — Identify functions and classes defined within Python files**  
*Verified.*  
Evidence: `get_functions_and_classes()` uses `ast.parse` and inspects `ast.ClassDef` and `ast.FunctionDef` nodes within each module.

### 2.3 Analysis Production

**R-F-8 — Produce an HTML documentation report from inspected sources**  
*Verified.*  
Evidence: The view assembles a context dictionary and renders `doc.html` via `render_template`.

**R-F-9 — Produce a rendered markdown equivalent for the same content**  
*Verified.*  
Evidence: `doc.md` template exists alongside `doc.html` and exposes identical context keys.

**R-F-10 — Expose the generated report at a URL keyed by repository owner and name**  
*Verified.*  
Evidence: The `/<repo_owner>/<repo_name>` route renders `doc.html` for the inspected repository.

### 2.4 User Interaction

**R-F-11 — Present a top-level landing page with a single analysis form**  
*Verified.*  
Evidence: `/` renders `index.html`, which contains a single form posting to `/submit`.

**R-F-12 — Accept form submissions via the `/submit` endpoint**  
*Verified.*  
Evidence: `application.py` registers `methods=['GET', 'POST']` on `/submit` and reads fields from `request.values`.

**R-F-13 — Redirect the user to the per-repository URL after a valid submission**  
*Verified.*  
Evidence: The controller calls `redirect(url_for('index', repo_owner=owner, repo_name=project))` following a successful acquisition.

---

## 3. Business and Domain Rules

**R-B-1 — Source identification must contain both owner and project identifiers**  
*Verified.*  
Evidence: `get_owner_and_repo()` returns two values derived from URL parsing; downstream routing requires both segments to construct the per-repository URL.

**R-B-2 — A repository submitted by URL must be reachable through a standard git transport that `gitpython`'s `clone_from` understands**  
*Inferred.*  
Evidence: The handler does not attempt to negotiate alternative protocols or authentication flows; failures bubble up as exceptions caught in `try` blocks.

**R-B-3 — The system extracts only Python-language symbols for documentation**  
*Verified.*  
Evidence: File filtering explicitly selects `.py` files and AST inspection looks for `FunctionDef`/`ClassDef` nodes only.

**R-B-4 — Decoding failures in source files must not abort analysis**  
*Verified.*  
Evidence: `open(file).read().decode('utf-8', errors='replace')` is the documented decoding policy.

**R-B-5 — The application limits the depth of recursion used in repository traversal**  
*Inferred.*  
Evidence: `get_python_files()` raises `RuntimeError` if the traversal depth exceeds 100, indicating a defensive upper bound rather than a domain rule per se.

**R-B-6 — State transitions on the `Repo` object: clone when remote, reuse when local**  
*Verified.*  
Evidence: `if local: Repo(local) else: Repo.clone_from(repo, dir_path)`.

---

## 4. Interface Requirements

### 4.1 HTTP Interface

**R-I-1 — The application serves a single Flask application with three route families**  
*Verified.*  
Evidence: `application.py` defines `/`, `/submit`, and `/<repo_owner>/<repo_name>`.

**R-I-2 — The landing form MUST submit the fields `repo` and `local` to `/submit`**  
*Verified.*  
Evidence: `index.html` names both inputs and sets `action="/submit"` with `method="post"`.

**R-I-3 — The system MUST accept both GET and POST on `/submit`**  
*Verified.*  
Evidence: `methods=['GET', 'POST']` on the route decorator.

**R-I-4 — Requests lacking recognized input MAY surface an internal error rather than a structured error response**  
*Uncertain.*  
Evidence: No explicit validation or error rendering branch exists for missing inputs in `application.py`; the behavior is determined by Flask's default handling of missing parameters.

**R-I-5 — The system renders templates `index.html`, `doc.html`, and `doc.md` as the canonical visual outputs**  
*Verified.*  
Evidence: `render_template` invocations reference these three files.

### 4.2 Template Contracts

**R-I-6 — `doc.html` MUST be renderable with context keys `repo`, `repo_owner`, `repo_name`, `files`, `output`, `error`, `raw`, `info`, `dir_path`**  
*Verified.*  
Evidence: The dictionary built in the controller matches the variables used in `doc.html`.

**R-I-7 — `doc.md` MUST be renderable with the same context keys as `doc.html`**  
*Verified.*  
Evidence: The `submit` route renders both templates with identical contexts.

### 4.3 External Protocol Usage

**R-I-8 — The application MUST perform git network operations through the `gitpython` library**  
*Verified.*  
Evidence: `from git import Repo` is the sole external source acquisition entry point.

**R-I-9 — Source files MUST be delivered to AST parsing as Python source text**  
*Verified.*  
Evidence: `ast.parse(content)` is invoked per file.

---

## 5. Data Requirements

**R-D-1 — The application MUST persist a clone of the target repository to a server-side working directory**  
*Verified.*  
Evidence: `dir_path = tempfile.mkdtemp()` and `Repo.clone_from(repo, dir_path)` materializes the repository to that path.

**R-D-2 — A unique working directory MUST be allocated per request**  
*Verified.*  
Evidence: `tempfile.mkdtemp()` is called for each invocation.

**R-D-3 — The system MUST identify subtrees by repository owner and repository name**  
*Verified.*  
Evidence: `get_owner_and_repo` returns owner and project and both are used in URL routing.

**R-D-4 — The system MUST collect a list of relative file paths belonging to the Python language subset**  
*Verified.*  
Evidence: `get_python_files()` returns `(file_path, file_name)` tuples appended to a list passed into the template context.

**R-D-5 — The system MUST capture per-file function names and per-file class names as derived data**  
*Verified.*  
Evidence: `get_functions_and_classes()` returns `(funcs, classes)`; both lists are appended into per-file dictionaries rendered in the templates.

**R-D-6 — No long-term storage of repositories or report content is implied**  
*Inferred.*  
Evidence: The application does not create persistent database tables or write user-visible artifacts outside the temporary working directory; `tempfile.mkdtemp()` directories are by definition transient.

---

## 6. Security Requirements

**R-S-1 — The application MUST receive repository sources over the public network without enforced authentication**  
*Verified.*  
Evidence: No authentication middleware, session check, or token verification is present in `application.py`; both `/` and `/submit` are unprotected.

**R-S-2 — The application MUST trust whatever URL or local path is submitted**  
*Verified.*  
Evidence: Inputs are passed directly to `Repo.clone_from` or `Repo(local)` without sanitization or allow-listing.

**R-S-3 — The application MUST execute arbitrary Python source files during analysis**  
*Verified.*  
Evidence: `ast.parse(content)` parses but does not execute Python; however, the broader system imports arbitrary user-supplied code in the templates (for example `{{ output }}` is rendered without escaping in the raw-markdown preview, as documented by the `raw` context flag).

**R-S-4 — The application MUST NOT log, redact, or otherwise protect credentials in transit**  
*Verified by absence.*  
Evidence: No credential handling, vault integration, or secret redaction logic exists in the repository.

**R-S-5 — All template output SHOULD be treated as untrusted because analysis results include raw source excerpts**  
*Inferred.*  
Evidence: `doc.html` and `doc.md` interpolate source strings via template variables; an `error` key in context is rendered with `{% raw %}{{ error }}{% endraw %}` in the markdown template, indicating deliberate raw rendering.

---

## 7. Non-Functional Requirements

**R-N-1 — The system MUST tolerate transient failures during repository cloning by surfacing them as visible error reports rather than crashing**  
*Inferred.*  
Evidence: `application.py` wraps acquisition and analysis in `try/except` blocks; caught exceptions populate the `error` context variable rendered in `doc.html`.

**R-N-2 — The system MUST bound traversal depth so that pathological repositories cannot exhaust the call stack**  
*Verified.*  
Evidence: Explicit `if recursion_depth > 100: raise RuntimeError` in `get_python_files()`.

**R-N-3 — The system SHOULD complete analyses within the duration tolerated by an interactive web session**  
*Uncertain.*  
Evidence: There is no caching, queueing, or asynchronous work; all processing is inline within the request handler, implying synchronous responsiveness is required.

**R-N-4 — The application MUST remain operable without an external database**  
*Verified.*  
Evidence: No database driver, ORM, or migration is present in the repository; only file system state and in-process memory are used.

**R-N-5 — The system SHOULD run on the Python version supported by the declared dependencies**  
*Inferred.*  
Evidence: `requirements.txt` pins `Flask`, `gitpython`, and `Markdown`; no Python version constraint is specified.

---

## 8. Operational and Deployment Requirements

**R-O-1 — The system MUST expose itself through a WSGI-compatible entry point**  
*Verified.*  
Evidence: `app.run()` in `application.py` is the standard Flask WSGI invocation; the module-level `app` object is the WSGI application.

**R-O-2 — The system MUST install dependencies listed in `requirements.txt`**  
*Verified.*  
Evidence: `requirements.txt` enumerates `flask`, `gitpython`, `markdown`.

**R-O-3 — The runtime environment MUST provide a working `git` binary because `gitpython` shells out for network and credential operations**  
*Inferred.*  
Evidence: `gitpython` is the only acquisition library and it depends on an external `git` executable on the host.

**R-O-4 — The runtime environment MUST grant filesystem write access to the temporary directory chosen by `tempfile`**  
*Verified.*  
Evidence: `tempfile.mkdtemp()` requires write access to the system temp directory.

**R-O-5 — The deployment MAY override the listening port and host**  
*Verified.*  
Evidence: `app.run(host='0.0.0.0', port=5000, debug=True)` documents the intended defaults.

**R-O-6 — The application MUST run with Flask debug mode enabled by default**  
*Verified.*  
Evidence: `debug=True` in `app.run()`.

**R-O-7 — No health-check, readiness, or liveness endpoint is required**  
*Verified by absence.*  
Evidence: Only the three documented routes exist; there are no `/health`, `/ready`, or `/metrics` endpoints.

**R-O-8 — The application MUST NOT require structured logging or external log aggregation**  
*Verified by absence.*  
Evidence: No logging configuration, log shipping, or metrics emission is present in the repository.

---

## 9. Documentation vs. Implementation Comparison

**R-X-1 — `README.md` describes a "Git repository documentation" feature, which is consistent with the implemented `/<owner>/<repo>` route**  
*Verified.*

**R-X-2 — The README and source both reference a `dir_path` template variable, but only `doc.html`/`doc.md` use it directly; this is consistent.**

**R-X-3 — The `doc.md` template uses `{% raw %}{{ error }}{% endraw %}` to render the error string verbatim. This raw-rendering convention is not documented elsewhere; if the original intent was to render markdown, the variable is misnamed. The discrepancy is small but worth noting.**

**R-X-4 — No acceptance tests, integration tests, or unit tests exist in the repository. Documentation cannot be cross-validated against executable assertions.**

---

## 10. Identified Gaps and Uncertainties

**R-G-1** — No explicit authentication, authorization, or rate-limiting requirement is established. The system is implicitly open to any caller.

**R-G-2** — No concurrency model is documented. Single-threaded synchronous execution is the only observed behavior.

**R-G-3** — No retention, cleanup, or eviction policy for temporary directories is implemented; whether the host system reclaims `tempfile.mkdtemp()` output is operating-system dependent.

**R-G-4** — The error-handling contract is informal: the system passes exception messages into template variables without structured error categories or HTTP status codes.

**R-G-5** — No evidence exists of any non-Python language support, despite `dir_path` and traversal logic being general; the Python-only filter is the only explicit constraint.

**R-G-6** — No internationalization, accessibility, or content-negotiation requirement is evidenced.

---

## 11. Requirement Inventory

| ID | Category | Certainty | Summary |
|----|----------|-----------|---------|
| R-F-1 | Functional | Verified | Accept remote git URL as primary input |
| R-F-2 | Functional | Verified | Accept optional local path as alternative input |
| R-F-3 | Functional | Verified | Acquire requested git repository locally |
| R-F-4 | Functional | Inferred | Reject requests without either source identifier |
| R-F-5 | Functional | Verified | Walk repo tree and select Python files |
| R-F-6 | Functional | Verified | Read textual content of each Python file |
| R-F-7 | Functional | Verified | Identify functions and classes per file |
| R-F-8 | Functional | Verified | Produce HTML documentation report |
| R-F-9 | Functional | Verified | Produce markdown report equivalent |
| R-F-10 | Functional | Verified | Expose report at per-repo URL |
| R-F-11 | Functional | Verified | Present landing page with single form |
| R-F-12 | Functional | Verified | Accept form submissions via /submit |
| R-F-13 | Functional | Verified | Redirect to per-repo URL after submission |
| R-B-1 | Domain | Verified | Source must contain owner and project |
| R-B-2 | Domain | Inferred | Remote sources must be reachable via standard git transport |
| R-B-3 | Domain | Verified | Only Python symbols are extracted |
| R-B-4 | Domain | Verified | Decode errors must not abort analysis |
| R-B-5 | Domain | Inferred | Recursion depth bounded defensively |
| R-B-6 | Domain | Verified | Clone when remote, reuse when local |
| R-I-1 | Interface | Verified | Flask app with three route families |
| R-I-2 | Interface | Verified | /submit receives `repo` and `local` |
| R-I-3 | Interface | Verified | /submit accepts GET and POST |
| R-I-4 | Interface | Uncertain | Missing inputs surface as Flask default error |
| R-I-5 | Interface | Verified | Renders index.html, doc.html, doc.md |
| R-I-6 | Interface | Verified | doc.html context keys specified |
| R-I-7 | Interface | Verified | doc.md shares context keys |
| R-I-8 | Interface | Verified | Source acquisition via gitpython |
| R-I-9 | Interface | Verified | Source delivered to AST as Python text |
| R-D-1 | Data | Verified | Persist clone to server-side working dir |
| R-D-2 | Data | Verified | Allocate unique working dir per request |
| R-D-3 | Data | Verified | Identify subtrees by owner and name |
| R-D-4 | Data | Verified | Collect relative paths of Python files |
| R-D-5 | Data | Verified | Capture function and class names per file |
| R-D-6 | Data | Inferred | No long-term storage implied |
| R-S-1 | Security | Verified | Public access without authentication |
| R-S-2 | Security | Verified | Inputs trusted without sanitization |
| R-S-3 | Security | Verified | Arbitrary source content rendered into templates |
| R-S-4 | Security | Verified (by absence) | No credential handling |
| R-S-5 | Security | Inferred | Report output treated as untrusted |
| R-N-1 | Non-functional | Inferred | Transient clone failures surfaced as errors |
| R-N-2 | Non-functional | Verified | Bounded traversal depth |
| R-N-3 | Non-functional | Uncertain | Interactive responsiveness implied |
| R-N-4 | Non-functional | Verified | Operable without external database |
| R-N-5 | Non-functional | Inferred | Python version constrained by dependencies |
| R-O-1 | Operational | Verified | WSGI entry point via Flask |
| R-O-2 | Operational | Verified | Install dependencies in requirements.txt |
| R-O-3 | Operational | Inferred | Runtime requires `git` binary |
| R-O-4 | Operational | Verified | Write access to system temp dir |
| R-O-5 | Operational | Verified | Host/port overridable |
| R-O-6 | Operational | Verified | Debug mode on by default |
| R-O-7 | Operational | Verified (by absence) | No health endpoints required |
| R-O-8 | Operational | Verified (by absence) | No structured logging required |
| R-X-1 | Doc-vs-Impl | Verified | README aligns with /<owner>/<repo> route |
| R-X-2 | Doc-vs-Impl | Verified | `dir_path` usage consistent |
| R-X-3 | Doc-vs-Impl | Verified | `{% raw %}` use in doc.md not externally documented |
| R-X-4 | Doc-vs-Impl | Verified | No tests present for cross-validation |