defmodule Fog.Gap do
  @moduledoc """
  A single gap in an agent's knowledge.

  GapKind encodes why the gap exists:
  - :known_unknown    — the agent knows it doesn't know this
  - :inferred_unknown — inferred from mesh topology / seam structure
  - :stale            — once known, now uncertain

  Confidence decays exponentially with time since last_seen.
  STALE gaps carry an additional ×0.5 penalty — they were known once.
  """

  @type kind :: :known_unknown | :inferred_unknown | :stale

  @type t :: %__MODULE__{
    key:        String.t(),
    kind:       kind(),
    domain:     String.t() | nil,
    confidence: float(),
    first_seen: integer(),
    last_seen:  integer(),
    metadata:   map()
  }

  defstruct [
    :key,
    :kind,
    domain:     nil,
    confidence: 1.0,
    first_seen: nil,
    last_seen:  nil,
    metadata:   %{}
  ]

  @default_half_life 7 * 24 * 3600  # 7 days in seconds

  @doc "Create a new gap, timestamped now."
  def new(key, kind, opts \\ []) do
    now = System.system_time(:second)
    %__MODULE__{
      key:        key,
      kind:       kind,
      domain:     Keyword.get(opts, :domain),
      confidence: Keyword.get(opts, :confidence, 1.0),
      metadata:   Keyword.get(opts, :metadata, %{}),
      first_seen: now,
      last_seen:  now
    }
  end

  @doc "Update last_seen to now."
  def touch(%__MODULE__{} = gap) do
    %{gap | last_seen: System.system_time(:second)}
  end

  @doc """
  Effective confidence after temporal decay.

      eff = confidence × exp(−λt)   where λ = ln(2) / half_life

  A gap unseen for one half_life period retains half its original confidence.
  STALE gaps carry an additional ×0.5 penalty.
  `half_life` is in seconds. Default: 7 days.
  """
  def effective_confidence(%__MODULE__{} = gap, half_life \\ @default_half_life, at \\ nil) do
    now = at || System.system_time(:second)
    t   = max(now - gap.last_seen, 0)
    lam = :math.log(2) / half_life
    decay = :math.exp(-lam * t)
    stale_penalty = if gap.kind == :stale, do: 0.5, else: 1.0
    gap.confidence * decay * stale_penalty
  end
end
