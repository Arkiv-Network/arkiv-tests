import { useCallback, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { JOBS_API_URL } from "../config/api";
import "./BrowseRepositoryPage.css";

/* ── types ── */

interface CommitPullRequest {
  number: number;
  title: string;
  url: string;
}

interface CommitEntry {
  commit: string;
  date: string;
  author: string;
  title: string;
  branch: string | null;
  parents: string[];
  pullRequest: CommitPullRequest | null;
  tags: string[];
}

/* ── helpers ── */

const DEFAULT_LIMIT = 30;
const LOAD_MORE_INCREMENT = 30;

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function shortSha(sha: string): string {
  return sha.slice(0, 7);
}

/* ── component ── */

export default function BrowseRepositoryPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const initialRepo = searchParams.get("repo") ?? "";

  const [repoInput, setRepoInput] = useState(initialRepo);
  const [commits, setCommits] = useState<CommitEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadedRepo, setLoadedRepo] = useState<string | null>(null);
  const [currentLimit, setCurrentLimit] = useState(DEFAULT_LIMIT);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const fetchCommits = useCallback(
    async (repo: string, limit: number) => {
      const trimmed = repo.trim();
      if (!trimmed) {
        setError("Please enter a repository in owner/repo format.");
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const response = await fetch(`${JOBS_API_URL}/commits`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ repo: trimmed, limit }),
        });

        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(
            (body as { error?: string }).error ??
              `Server responded with ${response.status}`
          );
        }

        const data = (await response.json()) as {
          repo: string;
          commits: CommitEntry[];
        };

        setCommits(data.commits);
        setLoadedRepo(data.repo);
        setCurrentLimit(limit);

        setSearchParams({ repo: data.repo }, { replace: true });
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    },
    [setSearchParams]
  );

  const handleLoad = () => {
    fetchCommits(repoInput, DEFAULT_LIMIT);
    setSelected(new Set());
  };

  const handleLoadMore = () => {
    const nextLimit = currentLimit + LOAD_MORE_INCREMENT;
    fetchCommits(repoInput, nextLimit);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleLoad();
  };

  const toggleSelect = (sha: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(sha)) {
        next.delete(sha);
      } else {
        next.add(sha);
      }
      return next;
    });
  };

  const handleCompare = () => {
    const shas = Array.from(selected);
    if (shas.length !== 2 || !loadedRepo) return;

    const params = new URLSearchParams({
      leftRepo: loadedRepo,
      leftRef: shas[0],
      rightRepo: loadedRepo,
      rightRef: shas[1],
    });
    navigate(`/?${params.toString()}`);
  };

  const handleClearSelection = () => setSelected(new Set());

  return (
    <div className="browse-repo-page">
      <div className="page-header">
        <h1>📋 Browse Repository</h1>
        <p className="page-subtitle">
          View recent commit history for any GitHub repository. Select two
          commits to compare their file trees.
        </p>
      </div>

      {/* ── controls ── */}
      <div className="browse-repo-controls">
        <div className="browse-repo-controls__field">
          <label htmlFor="browse-repo-input">Repository</label>
          <input
            id="browse-repo-input"
            type="text"
            placeholder="owner/repo (e.g. facebook/react)"
            value={repoInput}
            onChange={(e) => setRepoInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>
        <button
          type="button"
          className="browse-repo-controls__load-btn"
          onClick={handleLoad}
          disabled={loading || !repoInput.trim()}
        >
          {loading ? "Loading…" : "Load commits"}
        </button>
      </div>

      {/* ── error ── */}
      {error && <div className="browse-repo-error">{error}</div>}

      {/* ── empty state ── */}
      {!loading && commits.length === 0 && !error && (
        <div className="browse-repo-empty">
          <div className="browse-repo-empty__icon">📂</div>
          <h2>No commits loaded</h2>
          <p>
            Enter a GitHub repository name above and click{" "}
            <strong>Load commits</strong> to browse its history.
          </p>
        </div>
      )}

      {/* ── commit list ── */}
      {commits.length > 0 && (
        <>
          <div className="commit-list">
            <div className="commit-list__header">
              <span>Commits</span>
              {loadedRepo && (
                <span className="commit-list__header-repo">{loadedRepo}</span>
              )}
              <span className="commit-list__header-count">
                Showing {commits.length} commit{commits.length !== 1 && "s"}
              </span>
            </div>

            <div className="commit-list__body">
              {commits.map((c) => (
                <div
                  key={c.commit}
                  className={`commit-row${selected.has(c.commit) ? " commit-row--selected" : ""}`}
                >
                  {/* checkbox */}
                  <div className="commit-row__select">
                    <input
                      type="checkbox"
                      checked={selected.has(c.commit)}
                      onChange={() => toggleSelect(c.commit)}
                      aria-label={`Select commit ${shortSha(c.commit)}`}
                    />
                  </div>

                  {/* main content */}
                  <div className="commit-row__content">
                    <div className="commit-row__top">
                      <span className="commit-row__title">{c.title}</span>
                      <span className="commit-row__badges">
                        {c.branch && (
                          <span className="commit-badge commit-badge--branch">
                            🌿 {c.branch}
                          </span>
                        )}
                        {c.tags.map((tag) => (
                          <span
                            key={tag}
                            className="commit-badge commit-badge--tag"
                          >
                            🏷️ {tag}
                          </span>
                        ))}
                        {c.pullRequest && (
                          <span className="commit-badge commit-badge--pr">
                            PR #{c.pullRequest.number}
                          </span>
                        )}
                      </span>
                    </div>

                    <div className="commit-row__bottom">
                      <span className="commit-row__sha">
                        {shortSha(c.commit)}
                      </span>
                      <span className="commit-row__author">{c.author}</span>
                      <span className="commit-row__date">
                        {formatDate(c.date)}
                      </span>
                      {c.pullRequest && (
                        <a
                          className="commit-row__pr-link"
                          href={c.pullRequest.url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {c.pullRequest.title}
                        </a>
                      )}
                    </div>

                    {c.parents.length > 0 && (
                      <div className="commit-row__parents">
                        parents:{" "}
                        {c.parents.map((p, i) => (
                          <span key={p}>
                            {i > 0 && ", "}
                            <code>{shortSha(p)}</code>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* load more */}
          <div className="browse-repo-load-more">
            <button
              type="button"
              onClick={handleLoadMore}
              disabled={loading}
            >
              {loading ? "Loading…" : "Load more commits"}
            </button>
          </div>
        </>
      )}

      {/* ── compare bar ── */}
      {selected.size > 0 && (
        <div className="browse-repo-compare-bar">
          <div className="browse-repo-compare-bar__info">
            <strong>{selected.size}</strong> commit{selected.size !== 1 && "s"}{" "}
            selected
            {selected.size === 2
              ? " — ready to compare"
              : selected.size < 2
                ? " — select one more to compare"
                : " — select exactly 2 to compare"}
          </div>
          <div className="browse-repo-compare-bar__actions">
            <button
              type="button"
              className="browse-repo-compare-bar__btn"
              disabled={selected.size !== 2}
              onClick={handleCompare}
            >
              Compare selected
            </button>
            <button
              type="button"
              className="browse-repo-compare-bar__btn browse-repo-compare-bar__btn--clear"
              onClick={handleClearSelection}
            >
              Clear
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
