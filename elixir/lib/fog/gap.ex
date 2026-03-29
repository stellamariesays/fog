defmodule Fog.Gap do
  @moduledoc """
  A single gap in an agent's knowledge.

  GapKind encodes why the gap exists:
  - :known_unknown   — the agent knows it doesn't know this
  - :inferred_unknown — inferred from mesh topology / seam structure
  - :stale           — once known, now uncertain
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
end
