#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Source environment if present (.env preferred over .env.example)
if [[ -f .env ]]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' .env | xargs -I {} echo {}) 2>/dev/null || true
elif [[ -f .env.example ]]; then
  export $(grep -v '^#' .env.example | xargs -I {} echo {}) 2>/dev/null || true
fi

ARGS=()

# -------------------------------
# Existing graph build params
# -------------------------------
[[ -n "${SIMILAR_MIN_SHARED_SKILLS:-}" ]] && ARGS+=(--min-shared-skills "$SIMILAR_MIN_SHARED_SKILLS")
[[ -n "${SIMILAR_WEIGHT_MODE:-}"       ]] && ARGS+=(--weight-mode "$SIMILAR_WEIGHT_MODE")
[[ -n "${SIMILAR_BOOST_COMPANY:-}"     ]] && ARGS+=(--boost-company "$SIMILAR_BOOST_COMPANY")
[[ -n "${SIMILAR_BOOST_SCHOOL:-}"      ]] && ARGS+=(--boost-school "$SIMILAR_BOOST_SCHOOL")
[[ -n "${LOUVAIN_MAX_ITER:-}"          ]] && ARGS+=(--max-iter "$LOUVAIN_MAX_ITER")
[[ -n "${SIMILAR_EMBED_TOP_K:-}"       ]] && ARGS+=(--embed-top-k "$SIMILAR_EMBED_TOP_K")
[[ -n "${SIMILAR_EMBED_SCALE:-}"       ]] && ARGS+=(--embed-scale "$SIMILAR_EMBED_SCALE")
[[ -n "${GRAPH_METRICS_OUTPUT:-}"      ]] && ARGS+=(--output "$GRAPH_METRICS_OUTPUT")

# SIMILAR_EXCLUDE_IDS can be comma or space separated
if [[ -n "${SIMILAR_EXCLUDE_IDS:-}" ]]; then
  _EX_STR="${SIMILAR_EXCLUDE_IDS//,/ }"
  # shellcheck disable=SC2206
  _EX=(${_EX_STR})
  for id in "${_EX[@]}"; do
    [[ -n "$id" ]] && ARGS+=(--exclude "$id")
  done
fi

# -------------------------------
# Job-title layer params
# -------------------------------
# Path to JSON array with raw.linkedin* fields (optional)
_JOBS_JSON="${JOBS_JSON:-${JOBS_JSON_PATH:-}}"
[[ -n "${_JOBS_JSON:-}"            ]] && ARGS+=(--jobs-json "$_JOBS_JSON")
[[ -n "${TITLE_SYNONYMS_JSON:-}"   ]] && ARGS+=(--title-synonyms-json "$TITLE_SYNONYMS_JSON")
[[ -n "${JOB_EDGE_WEIGHT:-}"       ]] && ARGS+=(--job-edge-weight "$JOB_EDGE_WEIGHT")

# -------------------------------
# Ranker params
# -------------------------------
[[ -n "${RANK_GOAL_TEXT:-}"   ]] && ARGS+=(--rank-goal-text "$RANK_GOAL_TEXT")
[[ -n "${RANK_GOAL_TITLE:-}"  ]] && ARGS+=(--rank-goal-title "$RANK_GOAL_TITLE")

# RANK_GOAL_SKILLS can be comma or space separated
if [[ -n "${RANK_GOAL_SKILLS:-}" ]]; then
  _SK_STR="${RANK_GOAL_SKILLS//,/ }"
  # shellcheck disable=SC2206
  _SK=(${_SK_STR})
  if [[ ${#_SK[@]} -gt 0 ]]; then
    ARGS+=(--rank-goal-skills)
    for s in "${_SK[@]}"; do
      [[ -n "$s" ]] && ARGS+=("$s")
    done
  fi
fi

[[ -n "${RANK_ALPHA_SKILLS:-}"  ]] && ARGS+=(--rank-alpha-skills "$RANK_ALPHA_SKILLS")
[[ -n "${RANK_BETA_JOB:-}"      ]] && ARGS+=(--rank-beta-job "$RANK_BETA_JOB")
[[ -n "${RANK_GAMMA_STRUCT:-}"  ]] && ARGS+=(--rank-gamma-struct "$RANK_GAMMA_STRUCT")
[[ -n "${RANK_TOP_K:-}"         ]] && ARGS+=(--rank-top-k "$RANK_TOP_K")

# Boolean flag to write rank scores back to nodes
if [[ -n "${RANK_WRITE:-}" ]]; then
  ARGS+=(--rank-write)
fi

# -------------------------------
# Run
# -------------------------------
if [[ ${#ARGS[@]:-0} -eq 0 ]]; then
  echo "[precompute] No env-derived args. Proceeding with user args only: $*" >&2
else
  echo "[precompute] Running with env-derived args: ${ARGS[*]} (plus user args: $*)" >&2
fi

python precompute_graph.py ${ARGS[@]:+"${ARGS[@]}"} "$@"
